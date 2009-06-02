#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
# models.py - Qt models for views in userconfig                           #
# ------------------------------                                          #
# begin     : Tue May 26 2009                                             #
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
from PyKDE4.kdeui import KIconLoader

import locale

class UCAbstractItemModel(QAbstractItemModel):
    """ Item model for tree views in userconfig.  Common elements for
        users and groups.
    """
    column_data = []

    def __init__(self, parent, items):
        QAbstractItemModel.__init__(self, parent)
        self.items = items
        self.showsystemaccounts = True
    
    def columnCount(self, parent=None):
        return len(self.column_data)

    def rowCount(self, parent = QModelIndex()):
        if self.showsystemaccounts:
            return len(self.items)
        else:
            return len([obj for obj in self.items if not obj.isSystemAccount()])
    
    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column)
    
    def parent(self, index):
        return QModelIndex()
    
    def hasChildren(self, parent):
        if parent.row() > 0:
            return False
        else:
            return True

    def data(self, idx, role):
        if not idx.isValid():
            return QVariant()
        
        row = idx.row()
        if row >= self.rowCount():
            return QVariant()
        
        obj = self.items[row]
        while (not self.showsystemaccounts) and obj.isSystemAccount():
            row += 1
            try:
                obj = self.items[row]
            except IndexError:
                return QVariant()
        
        if role == Qt.DisplayRole:
            col = idx.column()
            return self._data(obj, col)
        elif role == Qt.EditRole:
            return QVariant(obj.getID())
        elif role == Qt.DecorationRole:
            col = idx.column()
            return self._icon_data(obj, col)
        else:
            return QVariant()

    def _data(self, obj, col):
        if self.column_data[col]["data_method_name"]:
            data_func = getattr(obj, self.column_data[col]["data_method_name"])
            return QVariant(data_func())
        else:
            return QVariant()
        
    def _icon_data(self, obj, col):
        return QVariant()
        
    def headerData(self, section, orientation, role):
        col = section
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.column_data[col]["header"])
        
        return QVariant()

    def slotShowSystemAccounts(self, on):
        self.showsystemaccounts = on
        self.emit(SIGNAL("modelReset()"))
        
    def setItems(self, items):
        self.items = items
        self.emit(SIGNAL("modelReset()"))
        
    def indexFromID(self, ID):
        for i, userobj in enumerate(self.items):
            if userobj.getID() == ID:
                return self.index(i, 0)
        return QModelIndex()


class UserModel(UCAbstractItemModel):
    """ Item model for tree views in userconfig.  Elements specific to users.
    """
    column_data = [ {"data_method_name" : "getRealName",
                     "header" : i18n("Real Name") },
                    {"data_method_name" : "getSystemName",
                     "header" : i18n("Username") },
                    {"data_method_name" : "",
                     "header" : "" },
                    ]
    
    def _icon_data(self, obj, col):
        if col == 2 and obj.isLocked():
                #print "object locked"
                #return QVariant("blah")
            return QVariant(KIconLoader.global_()
                            .loadIcon('object-locked', KIconLoader.Small))
        else:
            return QVariant()


class GroupModel(UCAbstractItemModel):
    """ Item model for tree views in userconfig.  Elements specific to groups.
    """
    column_data = [ {"data_method_name" : "getSystemName",
                     "header" : i18n("Group Name") },
                    {"data_method_name" : "getID",
                     "header" : i18n("GID") },
                    ]
