from .utils.configDict import ConfigDict

defaultConfig = {
    # the width of the popup window that shows multiline output
    'popupWidth' : 80,

    # the sign,it's highlighting and the line highlighting for invalid chunks.
    # The sign will be displayed in the sign bar and the whole chunk will be
    # highlighted with invalidLineHighlight
    'invalidSign'           : '>>', # '' (empty string) to disable
    'invalidSignHighlight'  : 'guibg=#782010', # guifg=None to disable
    'invalidLineHighlight'  : 'guibg=#141414', # guifg=None to disable

    # virtual text highlighting and priority
    'vtextPrompt'           : '>>', # '' to disable
    'vtextHighlight'        : 'gui=bold guifg=#ba4833', # guifg=None to disable
    'vtextStdoutHighlight'  : 'gui=bold guifg=#666666', # guifg=None to disable
    'vtextPriority'         : 200,

    # liveTriggerEvents:    the vim events that trigger the live callback
    # liveCommand:          the command to run when the live callback gets
    #                       called while live mode is enabled
    # semiLiveCommand:      the command to run when the live callback get
    #                       called while live mode is disabled
    'liveTriggerEvents'     : ['TextChanged', 'TextChangedI'],
    'liveCommand'           : 'TshunkyPyRunAllInvalid',
    'semiLiveCommand'       : 'TshunkyPyUpdate', #None to disable

    # alternate live command config
#   'liveTriggerEvents'     : ['CursorHold', 'CursorHoldI'],
#   'liveCommand'           : 'TshunkyPyRunAll',

    # whether the key mapping should be mapped in insert mode
    'enableInsertKeymaps'   : True,

    # the key of each config entry may be any vim command the value defines
    # the mapping to that command
    'keymap' : {'TshunkyPyUpdate'           : '<M-u>',
                'TshunkyPyRunAll'           : '<M-a>',
                'TshunkyPyRunAllInvalid'    : '<M-i>',
                'TshunkyPyRunFirstInvalid'  : '<M-f>',
                'TshunkyPyLive'             : '<M-x>',
                'TshunkyPyShowStdout'       : '<M-o>',
                'TshunkyPyQuit'             : '<M-q>'},

    # this option fixes a small bug, but it cost some computational time
    # if you're having issues with vtext positioning first try to set this
    # option to False.'
    'reuseCodeObjects'      : False,
}

config = ConfigDict()
config.update(defaultConfig)

if __name__ == '__main__':
    config.printToStdout()

