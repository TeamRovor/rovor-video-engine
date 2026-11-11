-- Read-only Moho project inventory for the Moho 14 command-line script runner.
-- Usage: ROVOR_MOHO_PROJECT=/absolute/file.moho Moho /absolute/moho_cli_inspect.lua
-- Optional: ROVOR_MOHO_REPORT=/absolute/report.json

local function jsonString(value)
    local s = tostring(value or '')
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\b', '\\b')
         :gsub('\f', '\\f'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
    return '"' .. s .. '"'
end

local function jsonNumber(value)
    local n = tonumber(value)
    if not n or n ~= n or n == math.huge or n == -math.huge then return 'null' end
    return string.format('%.9g', n)
end

local function layerType(layer)
    local kind = layer:LayerType()
    local names = {
        [MOHO.LT_VECTOR] = 'vector', [MOHO.LT_BONE] = 'bone',
        [MOHO.LT_GROUP] = 'group', [MOHO.LT_IMAGE] = 'image',
        [MOHO.LT_AUDIO] = 'audio', [MOHO.LT_SWITCH] = 'switch',
        [MOHO.LT_PARTICLE] = 'particle', [MOHO.LT_NOTE] = 'note',
        [MOHO.LT_PATCH] = 'patch'
    }
    return names[kind] or ('unknown:' .. tostring(kind))
end

local function inspectLayer(moho, layer, depth)
    if depth > 64 then error('Layer nesting exceeds safety limit') end
    local entry = {
        id = moho.document:LayerAbsoluteID(layer),
        name = layer:Name(),
        type = layerType(layer),
        visible = layer:IsVisible(),
        locked = layer:IsLocked(),
        children = {},
        bones = {},
        totalLayers = 1
    }
    if layer:IsBoneType() then
        local boneLayer = moho:LayerAsBone(layer)
        local skeleton = boneLayer:Skeleton()
        for i = 0, skeleton:CountBones() - 1 do
            local bone = skeleton:Bone(i)
            local pos = bone.fPos
            entry.bones[#entry.bones + 1] = {
                id = i, name = bone:Name(), parentId = bone.fParent or -1,
                x = pos and pos.x or 0, y = pos and pos.y or 0,
                angle = bone.fAngle or 0, scale = bone.fScale or 1,
                length = bone.fLength or 0
            }
        end
    end
    if layer:IsGroupType() then
        local group = moho:LayerAsGroup(layer)
        for i = 0, group:CountLayers() - 1 do
            local child = inspectLayer(moho, group:Layer(i), depth + 1)
            entry.children[#entry.children + 1] = child
            entry.totalLayers = entry.totalLayers + child.totalLayers
        end
    end
    return entry
end

local function encodeLayer(entry)
    local children, bones = {}, {}
    for i, child in ipairs(entry.children) do children[i] = encodeLayer(child) end
    for i, bone in ipairs(entry.bones) do
        bones[i] = '{"id":' .. jsonNumber(bone.id) .. ',"name":' .. jsonString(bone.name)
            .. ',"parentId":' .. jsonNumber(bone.parentId) .. ',"x":' .. jsonNumber(bone.x)
            .. ',"y":' .. jsonNumber(bone.y) .. ',"angle":' .. jsonNumber(bone.angle)
            .. ',"scale":' .. jsonNumber(bone.scale) .. ',"length":' .. jsonNumber(bone.length) .. '}'
    end
    return '{"id":' .. jsonNumber(entry.id) .. ',"name":' .. jsonString(entry.name)
        .. ',"type":' .. jsonString(entry.type) .. ',"visible":' .. tostring(entry.visible)
        .. ',"locked":' .. tostring(entry.locked) .. ',"children":[' .. table.concat(children, ',')
        .. '],"bones":[' .. table.concat(bones, ',') .. ']}'
end

local function writeResult(report)
    local layers = {}
    for i, layer in ipairs(report.layers) do layers[i] = encodeLayer(layer) end
    local text = '{"ok":' .. tostring(report.ok)
        .. ',"name":' .. jsonString(report.name)
        .. ',"path":' .. jsonString(report.path)
        .. ',"width":' .. jsonNumber(report.width)
        .. ',"height":' .. jsonNumber(report.height)
        .. ',"fps":' .. jsonNumber(report.fps)
        .. ',"startFrame":' .. jsonNumber(report.startFrame)
        .. ',"endFrame":' .. jsonNumber(report.endFrame)
        .. ',"topLayers":' .. jsonNumber(report.topLayers)
        .. ',"totalLayers":' .. jsonNumber(report.totalLayers)
        .. ',"layers":[' .. table.concat(layers, ',') .. ']'
        .. (report.error and (',"error":' .. jsonString(report.error)) or '') .. '}'
    local destination = os.getenv('ROVOR_MOHO_REPORT')
    if destination and destination ~= '' then
        local file, err = io.open(destination, 'w')
        if not file then error('Cannot write report: ' .. tostring(err)) end
        file:write(text, '\n')
        file:close()
    else
        print(text)
    end
end

function MohoScript(moho)
    local report = { ok = false, layers = {} }
    local ok, err = pcall(function()
        local project = os.getenv('ROVOR_MOHO_PROJECT')
        if project and project ~= '' then moho:FileOpen(project) end
        local doc = moho.document
        if not doc then error('No active Moho document; set ROVOR_MOHO_PROJECT') end
        report.name = doc:Name()
        report.path = doc:Path()
        report.width = doc:Width()
        report.height = doc:Height()
        report.fps = doc:Fps()
        report.startFrame = doc:StartFrame()
        report.endFrame = doc:EndFrame()
        report.topLayers = doc:CountLayers()
        report.totalLayers = 0
        for i = 0, doc:CountLayers() - 1 do
            local layer = inspectLayer(moho, doc:Layer(i), 0)
            report.layers[#report.layers + 1] = layer
            report.totalLayers = report.totalLayers + layer.totalLayers
        end
        report.ok = true
    end)
    if not ok then report.error = tostring(err) end
    writeResult(report)
    moho:Quit()
end
