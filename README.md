# tshunkyPy

tshunkyPy is an experimental neovim code runner plugin. It sits right in
the middle of the two major clusters of available code runner plugins. It runs
code in the correct context while avoiding to rerun the whole code all the
time.

## Why yet another code runner plugin?

I was looking for a (python) code runner plugin to be able to run and test
pieces of code and prototyp stuff on the fly.

As far as I know, the neovim code runner plugins available categorize in two
major branches both with their drawbacks.

On the one hand Codi, LuaPad,... rerun the entire code (buffer, file,...)
everytime an update event is triggerd. On the other hand vim-slime,
SnipRun,... send 'selected parts' of the code to an interpreter session and
disregard the context of the code (buffer, file,...).

tshunkyPy tries to fill the gap right in the middle. It considers the code
(buffer, file,...) in its entirety, while executing it in chunks (top level
statements). Furthermore it keeps track of dependencies of the chunks to one
another and only reruns chunks if the chunk itself or a chunk it depends on
(all the chunks 'above') changed. I.e. it makes sure that each chunk that is
executed will be executed in the correct context (of the buffer, file,...)
without rerunning it in it's entirety.

To achieve this tshunkyPy saves and restores the execution state for each
chunk. This is done -- broadly speaking -- by pickling `globals()`. As a result
this causes some restrictions to the ability of tshunkyPy as it is only able to
run code where the `globals()` ('variables and modules') are pickable. This
means that can't run code with tshunkyPy that for example uses file descriptors
or tracebacks in the main code (neovim buffer). Furthermore libraries such as
`matplotlib` and `subprocess` are not usable in the main code with tshunkyPy.

## demo
tshunkyPy in semi live mode (the TshunkyPy commands are map to keys by default, I manually typed them in the demo to show what's actually going on):

![](https://raw.githubusercontent.com/jeff-dh/tshunkyPy.nvim/master/screenshots/semiLive.gif)

tshunkyPy in live mode:

![](https://raw.githubusercontent.com/jeff-dh/tshunkyPy.nvim/master/screenshots/live.gif)

## install

install dill

```sh
pip install dill
```

install tshunkyPy with your package manager, for example with packer:

```lua
use {'jeff-dh/tshunkyPy.nvim', run=':UpdateRemotePlugins'},
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
    vtextPrompt           = '>>', -- '' to disable
    vtextHighlight        = 'gui=bold guifg=#ba4833', -- guifg=None to disable
    vtextStdoutHighlight  = 'gui=bold guifg=#666666', -- guifg=None to disable
    vtextPriority         = 200,

    -- liveTriggerEvents:    the vim events that trigger the live callback
    -- liveCommand:          the command to run when the live callback gets
    --                       called while live mode is enabled
    -- semiLiveCommand:      the command to run when the live callback get
    --                       called while live mode is disabled
    liveTriggerEvents     = {'CursorHold', 'CursorHoldI', 'TextChanged'},
    liveTriggerKeysI      = {'<CR>', '<UP>', '<DOWN>'},
    liveTriggerKeysN      = {'<CR>'},
    liveCommand           = 'TshunkyPyRunAllInvalid',
    semiLiveCommand       = 'TshunkyPyUpdate', --None to disable

    -- whether the key mapping should be mapped in insert mode
    enableInsertKeymaps   = true,

    -- the key of each config entry may be any vim command the value defines
    -- the mapping to that command
    keymap = { TshunkyPyUpdate           = '<M-u>', -- '' to disable
               TshunkyPyRunAll           = '<M-a>', -- '' to disable
               TshunkyPyRunAllInvalid    = '<M-i>', -- '' to disable
               TshunkyPyRunFirstInvalid  = '<M-f>', -- '' to disable
               TshunkyPyRunRange         = '<M-r>', -- '' to disable
               TshunkyPyLive             = '<M-x>', -- '' to disable
               TshunkyPyShowStdout       = '<M-o>', -- '' to disable
               TshunkyPyQuit             = '<M-q>'},-- '' to disable

    -- this option fixes a small bug, but it cost some computational time
    reuseCodeObjects      = false,
})
```
