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
    
    def columnCount(self, parent=None):
        return len(self.column_data)

    def rowCount(self, parent = QModelIndex()):
        return len(self.items)
    
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
        obj = self.objData(idx)
        if obj is None:
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
    
    def objData(self, idx):
        if not idx.isValid():
            return None
        
        row = idx.row()
        if row >= self.rowCount():
            return None
        
        obj = self.items[row]
        return obj
    
    def headerData(self, section, orientation, role):
        col = section
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.column_data[col]["header"])
        
        return QVariant()
        
    def setItems(self, items):
        self.items = items
        self.emit(SIGNAL("modelReset()"))
        
    def indexFromID(self, ID):
        for i, obj in enumerate(self.items):
            if obj.getID() == ID:
                return self.index(i, 0)
        return QModelIndex()
    
    def indexFromSystemName(self, name):
        for i, obj in enumerate(self.items):
            if obj.getSystemName() == name:
                return self.index(i, 0)
        return QModelIndex()
        
    def selectionFromID(self, ID):
        for i, obj in enumerate(self.items):
            if obj.getID() == ID:
                return QItemSelection(self.index(i, 0),
                                      self.index(i, self.columnCount() - 1))
        return QItemSelection()


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


class FilterSystemAcctsProxyModel(QSortFilterProxyModel):
    """ Proxy model to filter out system accounts from a group or user model """

    def filterAcceptsRow(self, source_row, source_parent=QModelIndex()):
        sourceIndex = self.sourceModel().index(source_row, 0, source_parent)
        obj = self.sourceModel().objData(sourceIndex)
        return not obj.isSystemAccount()


class GroupListModel(UCAbstractItemModel):
    """ Item model for list views in userconfig.  Allows groups to be checked.
    """
    
    def __init__(self, parent, items, userobj):
        UCAbstractItemModel.__init__(self, parent, items)
        self.userobj = userobj

    def setUser(self, userobj):
        self.userobj = userobj
        self.emit(SIGNAL("modelReset()"))
    
    def _primaryGroupRow(self):
        if self.userobj is not None:
            for i, group in enumerate(self.items):
                if group is self.userobj.getPrimaryGroup():
                    return i
        return None
    
    def flags(self, idx):
        if idx.isValid() and idx.row() == self._primaryGroupRow():
            return Qt.ItemFlag(Qt.ItemIsEnabled)
        else:
            return Qt.ItemFlag(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
    
    def columnCount(self, parent=None):
        return 1
    
    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, 0)

    def data(self, idx, role):
        obj = self.objData(idx)
        if obj is None:
            return QVariant()
        
        if role == Qt.DisplayRole:
            return QVariant(obj.getGroupname())
        elif role == Qt.EditRole:
            return QVariant(obj.getID())
        elif role == Qt.CheckStateRole:
            # No checkbox for the primary group (nevermind, looks ugly)
            #if idx.row() == self._primaryGroupRow():
                #return QVariant()
            check = Qt.Unchecked
            if obj in self.userobj.getGroups():
                check = Qt.Checked
            return QVariant(check)
        else:
            return QVariant()
    
    def setData(self, idx, val, role):
        obj = self.objData(idx)
        if obj is None:
            return False
        
        if role == Qt.CheckStateRole:
            if obj is self.userobj.getPrimaryGroup():
                return False
            if val.toInt()[0] == Qt.Checked:
                self.userobj.addToGroup(obj)
            else:
                self.userobj.removeFromGroup(obj)
            # dataChanged doesn't seem to get the other view to repaint right
            #   away, so modelReset will have to do.  Should be fine for
            #   this size data set.
            #self.emit(SIGNAL("dataChanged(QModelIndex&,QModelIndex&)"), idx, idx)
            self.emit(SIGNAL("modelReset()"))
            return True
        else:
            return False
        
    def headerData(self, section, orientation, role):
        return QVariant()


class SimpleGroupListProxyModel(QSortFilterProxyModel):
    """ Group list model without checkboxes """
    
    def flags(self, idx=None):
        return Qt.ItemFlag(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    def data(self, idx, role):
        if role == Qt.CheckStateRole:
            return QVariant()
        elif role == Qt.EditRole:
            # Needed for combo box
            return QSortFilterProxyModel.data(self, idx, Qt.DisplayRole)
        else:
            return QSortFilterProxyModel.data(self, idx, role)


class PrivilegeListProxyModel(QSortFilterProxyModel):
    """ Proxy model to show just groups with known privilege descriptions
        and show those descriptions instead of the group names.
    """
    
    privilege_names = {
            "plugdev" : i18n("Access external storage devices automatically"),
            "adm" : i18n("Administer the system"),
            "ltsp" : i18n("Allow use of FUSE filesystems like LTSP thin " +
                          "client block devices"),
            "dialout" : i18n("Connect to the Internet using a modem"),
            "syslog" : i18n("Monitor system logs"),
            "fax" : i18n("Send and receive faxes"),
            "cdrom" : i18n("Use CD-ROM and DVD drives"),
            "floppy" : i18n("Use floppy drives"),
            "modem" : i18n("Use modems"),
            "scanner" : i18n("Use scanners"),
        }

    def filterAcceptsRow(self, source_row, source_parent=QModelIndex()):
        sourceIndex = self.sourceModel().index(source_row, 0, source_parent)
        group_name = self.sourceModel().data(sourceIndex, Qt.DisplayRole)\
                                                                .toString()
        return str(group_name) in self.privilege_names

    def data(self, idx, role):
        data = QSortFilterProxyModel.data(self, idx, role)
        if data.isValid() and role == Qt.DisplayRole:
            data = self.privilege_names[str(data.toString())]
            return QVariant(data)
        else:
            return data
