-- DCS Mission Maker: server-side load check.
--
-- Install on the machine running DCS (dedicated server or the PC you host from):
--   Saved Games\DCS.server\Scripts\Hooks\dmm_reporter.lua   (or Saved Games\DCS\...)
-- Download it from the app (/dcs-hook.lua) so APP_URL below is filled in.
--
-- 1. Load check: a minute after a mission starts it scans dcs.log for script
--    errors logged since the mission began loading and reports them to the app
--    ("Recent missions" and the Briefing Room).
-- 2. Debrief: it records kills, losses, ejections, crashes, take-offs and
--    landings, reads the mission's objective flags (9000 = all done, 9001+ =
--    each objective), and sends them to the app every minute and when the
--    mission ends. The Briefing Room's Debrief tab shows the result.
-- 3. Liveries: once per DCS session it lists the liveries installed on this
--    machine (DCS install and Saved Games\Liveries) so the app's livery
--    dropdowns show every livery your server has, by its in-game name.
-- EXPERIMENTAL: not yet tested inside DCS.

local APP_URL = "__APP_URL__"
local CHECK_AFTER_SECONDS = 60
local DEBRIEF_EVERY_SECONDS = 60
local FIRST_FLAG, LAST_FLAG = 9000, 9010
local MAX_EVENTS = 500

package.path = package.path .. ";.\\LuaSocket\\?.lua"
package.cpath = package.cpath .. ";.\\LuaSocket\\?.dll"
local ok_http, http = pcall(require, "socket.http")
local ok_ltn, ltn12 = pcall(require, "ltn12")

local dmm = { logOffset = 0, checkAt = nil, mission = "", events = {}, sent = 0, debriefAt = nil,
              liveriesSent = false }
local logPath = lfs.writedir() .. "Logs\\dcs.log"

local function fileSize(path)
  local f = io.open(path, "rb")
  if not f then return 0 end
  local size = f:seek("end")
  f:close()
  return size or 0
end

local function jsonString(s)
  s = tostring(s):gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\r', ''):gsub('\n', '\\n')
  return '"' .. s:gsub('[%c]', ' ') .. '"'
end

local function scanErrors()
  local f = io.open(logPath, "rb")
  if not f then return { "Could not open dcs.log" } end
  f:seek("set", dmm.logOffset)
  local errors = {}
  for line in f:lines() do
    if line:find("ERROR") and (line:find("SCRIPTING") or line:find("LuaNET")
        or line:find("Mission script error") or line:find("DO SCRIPT")) then
      errors[#errors + 1] = line:sub(1, 400)
      if #errors >= 25 then break end
    end
  end
  f:close()
  return errors
end

local function post(path, body)
  if not (ok_http and ok_ltn) then
    log.write("DMM", log.ERROR, "LuaSocket not available; can't report to " .. APP_URL)
    return nil
  end
  local _, code = http.request({
    url = APP_URL .. path, method = "POST",
    headers = { ["Content-Type"] = "application/json", ["Content-Length"] = tostring(#body) },
    source = ltn12.source.string(body),
  })
  return code
end

local function report(errors)
  local parts = {}
  for i, e in ipairs(errors) do parts[i] = jsonString(e) end
  local body = '{"mission":' .. jsonString(dmm.mission) .. ',"errors":[' .. table.concat(parts, ",") .. ']}'
  local code = post("/api/reports", body)
  log.write("DMM", log.INFO, "Reported " .. #errors .. " error(s) for " .. dmm.mission .. " -> HTTP " .. tostring(code))
end

-- ------------------------------------------------------------------- debrief
local function unitName(unitId)
  if not unitId then return nil end
  local ok, name = pcall(DCS.getUnitProperty, tonumber(unitId), DCS.UNIT_NAME)
  if ok and name and name ~= "" then return name end
  return nil
end

local function playerName(id)
  if not id or id < 1 then return nil end
  local ok, name = pcall(net.get_player_info, id, "name")
  if ok then return name end
  return nil
end

-- The slot (unit) a player is in, e.g. "Viper 1-2 (Mitsu)".
local function playerUnit(id)
  if not id or id < 1 then return nil end
  local ok, slot = pcall(net.get_player_info, id, "slot")
  if ok and slot and slot ~= "" then return unitName(slot) end
  return nil
end

local function record(e)
  if #dmm.events >= MAX_EVENTS then return end
  e.t = math.floor(DCS.getModelTime())
  dmm.events[#dmm.events + 1] = e
end

local function readFlag(n)
  local code = "return tostring(trigger.misc.getUserFlag(" .. n .. "))"
  for _, state in ipairs({ "server", "mission" }) do
    local ok, value = pcall(net.dostring_in, state, code)
    if ok and value and tonumber(value) then return tonumber(value) end
  end
  return nil
end

local function sendDebrief(final)
  local flags = {}
  for n = FIRST_FLAG, LAST_FLAG do
    local v = readFlag(n)
    if v then flags[tostring(n)] = v end
  end
  local fresh = {}
  for i = dmm.sent + 1, #dmm.events do fresh[#fresh + 1] = dmm.events[i] end
  if #fresh == 0 and not final and next(flags) == nil then return end
  local ok, body = pcall(net.lua2json, {
    mission = dmm.mission, from = dmm.sent, events = fresh, flags = flags,
    final = final and true or false, time = math.floor(DCS.getModelTime()),
  })
  if not ok then
    log.write("DMM", log.ERROR, "Could not encode debrief: " .. tostring(body))
    return
  end
  local code = post("/api/debrief", body)
  if code == 200 then dmm.sent = dmm.sent + #fresh end
end

-- ------------------------------------------------------------------ liveries
local MAX_PER_TYPE = 400

local function liveryName(dir)
  local f = io.open(dir .. "\\description.lua", "r")
  if not f then return nil end
  local text = f:read("*a") or ""
  f:close()
  return text:match('[^_%w]name%s*=%s*"([^"]+)"') or text:match("^name%s*=%s*\"([^\"]+)\"")
end

-- Adds every <type>\<livery> under a Liveries folder to found[type].
local function scanLiveries(root, found)
  if lfs.attributes(root, "mode") ~= "directory" then return end
  for typeName in lfs.dir(root) do
    local typeDir = root .. "\\" .. typeName
    if typeName ~= "." and typeName ~= ".." and lfs.attributes(typeDir, "mode") == "directory" then
      local list = found[typeName] or {}
      found[typeName] = list
      for entry in lfs.dir(typeDir) do
        local path = typeDir .. "\\" .. entry
        local mode = lfs.attributes(path, "mode")
        if #list < MAX_PER_TYPE and entry ~= "." and entry ~= ".." then
          if mode == "directory" then
            list[#list + 1] = { id = entry, name = liveryName(path) or entry }
          elseif mode == "file" and entry:lower():match("%.zip$") then
            local id = entry:sub(1, -5)
            list[#list + 1] = { id = id, name = id }
          end
        end
      end
    end
  end
end

-- Liveries live in Bazar, in each module's own folder, and in Saved Games.
local function installedLiveries()
  local found, install = {}, lfs.currentdir()
  if not install:match("[\\/]$") then install = install .. "\\" end
  scanLiveries(install .. "Bazar\\Liveries", found)
  for _, base in ipairs({ "CoreMods\\aircraft", "Mods\\aircraft", "CoreMods\\WWII Units" }) do
    local dir = install .. base
    if lfs.attributes(dir, "mode") == "directory" then
      for module in lfs.dir(dir) do
        if module ~= "." and module ~= ".." then scanLiveries(dir .. "\\" .. module .. "\\Liveries", found) end
      end
    end
  end
  local saved = lfs.writedir()
  if not saved:match("[\\/]$") then saved = saved .. "\\" end
  scanLiveries(saved .. "Liveries", found)
  return found
end

local function sendLiveries()
  local ok, body = pcall(net.lua2json, { types = installedLiveries() })
  if not ok then
    log.write("DMM", log.ERROR, "Could not encode liveries: " .. tostring(body))
    return
  end
  local code = post("/api/liveries", body)
  dmm.liveriesSent = code == 200
  log.write("DMM", log.INFO, "Sent installed liveries -> HTTP " .. tostring(code))
end

local events = {}

function events.kill(killerId, killerType, killerSide, victimId, victimType, victimSide, weapon)
  record({ type = "kill", player = playerName(killerId), unit = playerUnit(killerId),
           killer_type = killerType, killer_side = killerSide, victim_player = playerName(victimId),
           victim_unit = playerUnit(victimId), victim_type = victimType, victim_side = victimSide,
           weapon = weapon })
end

for _, name in ipairs({ "crash", "eject", "pilot_death" }) do
  events[name] = function(playerId, unitId)
    record({ type = name, player = playerName(playerId), unit = unitName(unitId) or playerUnit(playerId) })
  end
end

for _, name in ipairs({ "takeoff", "landing" }) do
  events[name] = function(playerId, unitId, place)
    record({ type = name, player = playerName(playerId), unit = unitName(unitId) or playerUnit(playerId),
             place = place })
  end
end

function events.friendly_fire(playerId, weapon, victimId)
  record({ type = "friendly_fire", player = playerName(playerId), unit = playerUnit(playerId),
           victim_player = playerName(victimId), weapon = weapon })
end

function events.mission_end(winner, msg)
  record({ type = "mission_end", winner = winner, text = msg })
end

local callbacks = {}

function callbacks.onMissionLoadBegin()
  dmm.logOffset = fileSize(logPath)
  dmm.checkAt = nil
  dmm.events, dmm.sent, dmm.debriefAt = {}, 0, nil
end

function callbacks.onSimulationStart()
  dmm.mission = DCS.getMissionFilename and DCS.getMissionFilename() or DCS.getMissionName()
  dmm.mission = tostring(dmm.mission):match("([^\\/]+)$") or dmm.mission
  dmm.checkAt = DCS.getRealTime() + CHECK_AFTER_SECONDS
  dmm.debriefAt = DCS.getRealTime() + DEBRIEF_EVERY_SECONDS
  if not dmm.liveriesSent then
    local ok, err = pcall(sendLiveries)
    if not ok then log.write("DMM", log.ERROR, "liveries: " .. tostring(err)) end
  end
end

function callbacks.onGameEvent(name, ...)
  local handler = events[name]
  if handler and dmm.mission ~= "" then
    local ok, err = pcall(handler, ...)
    if not ok then log.write("DMM", log.ERROR, "event " .. tostring(name) .. ": " .. tostring(err)) end
  end
end

function callbacks.onSimulationStop()
  if dmm.mission ~= "" then
    local ok, err = pcall(sendDebrief, true)
    if not ok then log.write("DMM", log.ERROR, tostring(err)) end
  end
  dmm.debriefAt = nil
end

function callbacks.onSimulationFrame()
  if dmm.checkAt and DCS.getRealTime() >= dmm.checkAt then
    dmm.checkAt = nil
    local ok, err = pcall(function() report(scanErrors()) end)
    if not ok then log.write("DMM", log.ERROR, tostring(err)) end
  end
  if dmm.debriefAt and DCS.getRealTime() >= dmm.debriefAt then
    dmm.debriefAt = DCS.getRealTime() + DEBRIEF_EVERY_SECONDS
    local ok, err = pcall(sendDebrief, false)
    if not ok then log.write("DMM", log.ERROR, tostring(err)) end
  end
end

DCS.setUserCallbacks(callbacks)
log.write("DMM", log.INFO, "DCS Mission Maker reporter loaded, reporting to " .. APP_URL)
