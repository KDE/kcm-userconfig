#!/usr/bin/python
# -*- coding: UTF-8 -*-
###########################################################################
# groups.py - utility functions for userconfig                            #
# ------------------------------                                          #
# begin     : Wed Apr 30 2003                                             #
# copyright : (C) 2003-2006 by Simon Edwards, 2008 by Yuriy Kozlov        #
# email     : simon@simonzone.com                                         #
#                                                                         #
###########################################################################
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
###########################################################################

# KDE imports
from PyKDE4.kdecore import *

import locale

# Rudd-O convenience class to map groups to privilege names
class PrivilegeNames(dict):
    """Convenience dict-derived class: map known secondary groups to privilege names, provide default mapping for groups that do not have a description.  This could be replaced by a simple dict() but I simply preferred the class declaration.
    
    FIXME This should ideally be included in a more general module so it can be reused."""

    def __init__(self):
        dict.__init__(self, {
            "plugdev":i18n("Access external storage devices automatically"),
            "adm":i18n("Administer the system"),
            "ltsp":i18n("Allow use of FUSE filesystems like LTSP thin client block devices"),
            "dialout":i18n("Connect to the Internet using a modem"),
            "syslog":i18n("Monitor system logs"),
            "fax":i18n("Send and receive faxes"),
            "cdrom":i18n("Use CD-ROM and DVD drives"),
            "floppy":i18n("Use floppy drives"),
            "modem":i18n("Use modems"),
            "scanner":i18n("Use scanners"),
        })

    def __getitem__(self,name):
        # This is cruft but I couldn't bring myself to kill it bua!
        if name in self: return dict.__getitem__(self,name)
        return i18n("Be a member of the %s group")%name