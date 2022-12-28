-- Save copied tables in `copies`, indexed by original table.
function deepcopy(orig, copies)
    copies = copies or {}
    local orig_type = type(orig)
    local copy
    if orig_type == 'table' then
        if copies[orig] then
            copy = copies[orig]
        else
            copy = {}
            copies[orig] = copy
            for orig_key, orig_value in next, orig, nil do
                copy[deepcopy(orig_key, copies)] = deepcopy(orig_value, copies)
            end
            setmetatable(copy, deepcopy(getmetatable(orig), copies))
        end
    else -- number, string, boolean, etc
        copy = orig
    end
    return copy
end

local function runInContext(code, context)
    setmetatable(context, { __index = _G})

    local f, result = load(code, 'filename', 't', context)
    assert(f)
    f()
end

local function runTest()
    local code = [[
    function foo()
        print(abc)
    end]]

    local code2 = 'foo()'
    local code3 = "abc = 'xyz'"
    local code4 = 'print(abc)'

    local context = {}

    runInContext(code, context)

    local context2 = deepcopy(context)
    context2.abc = 'abc'
    runInContext(code2, context)
    local context3 = deepcopy(context2)
    runInContext(code3, context)

    context2.abc = 'abc'
    runInContext(code2, context)

    runInContext(code4, context3)
    runInContext(code4, context2)
    runInContext(code4, context)
end

return {runTest = runTest}
