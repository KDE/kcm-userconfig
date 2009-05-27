#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
# models.py - Qt models for views in userconfig                           #
# ------------------------------                                          #
# begin     : Wed Apr 30 2003                                             #
# copyright : (C) 2009 by Yuriy Kozlov                                    #
# email     : yuriy-kozlov@kubuntu.org                                    #
#                                                                         #
###########################################################################
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
###########################################################################

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# KDE imports
from PyKDE4.kdecore import *

import locale

class UCAbstractItemModel(QAbstractItemModel):
    def __init__(self, parent):
        QAbstractItemModel.__init__(self, parent)
        self.showsystemaccounts = True

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def hasChildren(self, parent):
        if parent.row() >= 0:
            return False
        else:
            return True

    def slotShowSystemAccounts(self, on):
        self.showsystemaccounts = on
        self.emit(SIGNAL("modelReset()"))


class UserModel(UCAbstractItemModel):
    def __init__(self, parent, admincontext):
        UCAbstractItemModel.__init__(self, parent)
        self.items = admincontext.getUsers()
    
    def indexFromUID(self, uid):
        for i, userobj in enumerate(self.items):
            if userobj.getUID() == uid:
                return self.index(i, 0)
        return QModelIndex()
    
    def rowCount(self, parent):
        if self.showsystemaccounts:
            return len(self.items)
        else:
            return len([user for user in self.items if not user.isSystemUser()])
    
    def columnCount(self, parent):
        return 2
    
    def data(self, idx, role):
        if not idx.isValid():
            return QVariant()
        
        row = idx.row()
            
        userobj = self.items[row]
        while (not self.showsystemaccounts) and userobj.isSystemUser():
            row += 1
            try:
                userobj = self.items[row]
            except IndexError:
                return QVariant()
        
        if role == Qt.DisplayRole:
            col = idx.column()
            if col == 0:
                return QVariant(userobj.getRealName())
            elif col == 1:
                return QVariant(userobj.getUsername())
        elif role == Qt.EditRole:
            return QVariant(userobj.getUID())
        else:
            return QVariant()
            
    def headerData(self, section, orientation, role):
        col = section
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if col == 0:
                return QVariant(i18n("Real Name"))
            elif col == 1:
                return QVariant(i18n("Username"))
        
        return QVariant()


class GroupModel(UCAbstractItemModel):
    def __init__(self, parent, admincontext):
        UCAbstractItemModel.__init__(self, parent)
        self.items = admincontext.getGroups()
    
    def indexFromUID(self, uid):
        for i, userobj in enumerate(self.items):
            if userobj.getUID() == uid:
                return self.index(i, 0)
        return QModelIndex()
    
    def rowCount(self, parent):
        if self.showsystemaccounts:
            return len(self.items)
        else:
            return len([group for group in self.items if not group.isSystemGroup()])
    
    def columnCount(self, parent):
        return 2
    
    def data(self, idx, role):
        if not idx.isValid():
            return QVariant()
        
        row = idx.row()
            
        groupobj = self.items[row]
        while (not self.showsystemaccounts) and groupobj.isSystemGroup():
            row += 1
            try:
                groupobj = self.items[row]
            except IndexError:
                return QVariant()
        
        if role == Qt.DisplayRole:
            col = idx.column()
            if col == 0:
                return QVariant(groupobj.getGroupname())
            elif col == 1:
                return QVariant(unicode(groupobj.getGID()))
        elif role == Qt.EditRole:
            return QVariant(groupobj.getGID())
        else:
            return QVariant()
            
    def headerData(self, section, orientation, role):
        col = section
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if col == 0:
                return QVariant(i18n("Group Name"))
            elif col == 1:
                return QVariant(i18n("GID"))
        
        return QVariant()
