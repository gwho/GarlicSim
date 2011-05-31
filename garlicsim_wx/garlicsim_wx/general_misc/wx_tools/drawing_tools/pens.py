# Copyright 2009-2011 Ram Rachum.
# This program is distributed under the LGPL2.1 license.

'''
This module defines the `` class.

See its documentation for more information.
'''

import wx

from garlicsim.general_misc import caching


is_mac = (wx.Platform == '__WXMAC__')
is_gtk = (wx.Platform == '__WXGTK__')
is_win = (wx.Platform == '__WXMSW__')


@caching.cache(max_size=100)
def get_selection_pen(color='black', dashes=[1, 4]):
    ''' '''
    if isinstance(color, basestring):
        color = wx.NamedColour(color)
        
    # blocktodoc: do `if is_mac`, also gtk maybe
    
    pen = wx.Pen(color, 1, wx.USER_DASH)
    pen.SetDashes(dashes)
    return pen
    
    