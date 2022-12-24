# tshunkyPy
A neovim plugin that runs python code right after you typed it

## install

install dill

```sh
pip install dill
```

install tshunkyPy with your package manager, for example with packer:

```lua
use 'jeff-dh/tshunkyPy.nvim'
```


## config

You don't need to call the `setup` function, but you can. You can provide a
table that overwrites the default values shown in the config below.

I have mapped `<leader>p` to the `TshunkyPy` command in my nvim config to start
tshunkyPy quickly for any open buffer and afterwards I can control tshunkyPy in
normal aswell as in insert mode with the default key mappings.

```lua
require('tshunkyPy').setup({
    -- the width of the popup window that shows multiline output
    popupWidth = 80,

    -- the sign,it's highlighting and the line highlighting for invalid chunks.
    -- The sign will be displayed in the sign bar and the whole chunk will be
    -- highlighted with invalidLineHighlight
    invalidSign           = '>>', -- '' (empty string) to disable
    invalidSignHighlight  = 'guibg=#782010', -- guifg=None to disable
    invalidLineHighlight  = 'guibg=#141414', -- guifg=None to disable

    -- virtual text highlighting and priority
    vtextHighlight        = 'gui=bold guifg=#ba4833', -- guifg=None to disable
    vtextPriority         = 200,

    -- liveTriggerEvents:    the vim events that trigger the live callback
    -- liveCommand:          the command to run when the live callback gets
    --                       called while live mode is enabled
    -- semiLiveCommand:      the command to run when the live callback get
    --                       called while live mode is disabled
    liveTriggerEvents     = {'TextChanged', 'TextChangedI'},
    liveCommand           = 'TshunkyPyRunAllInvalid',
    semiLiveCommand       = 'TshunkyPyUpdate', --None to disable

    -- alternate live command config
--  liveTriggerEvents     = ['CursorHold', 'CursorHoldI'],
--  liveCommand           = 'TshunkyPyRunAll',

    -- whether the key mapping should be mapped in insert mode
    enableInsertKeymaps   = true,

    -- the key of each config entry may be any vim command the value defines
    -- the mapping to that command
    keymap = { TshunkyPyUpdate           = '<M-u>', -- '' to disable
               TshunkyPyRunAll           = '<M-a>', -- '' to disable
               TshunkyPyRunAllInvalid    = '<M-i>', -- '' to disable
               TshunkyPyRunFirstInvalid  = '<M-f>', -- '' to disable
               TshunkyPyLive             = '<M-x>', -- '' to disable
               TshunkyPyShowStdout       = '<M-o>', -- '' to disable
               TshunkyPyQuit             = '<M-q>'},-- '' to disable

    -- this option fixes a small bug, but it cost some computational time
    reuseCodeObjects      = false,
})
```
