#!/usr/bin/python
# -*- coding: UTF-8 -*-
###########################################################################
# userconfig.py - description                                             #
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

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# KDE imports
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

import locale

class GroupEditDialog(KDialog):
    def __init__(self,parent,admincontext):
        #KDialogBase.__init__(self,parent,None,True,i18n("Edit Group"),KDialogBase.Ok|KDialogBase.Cancel,
            #KDialogBase.Cancel)
        KDialog.__init__(self, parent)
        self.setModal(True)
        self.setCaption(i18n("Edit Group"))
        #self.setButtons(KDialog.Ok|KDialog.Cancel) # TODO

        self.admincontext = admincontext

        topvbox = KVBox(self)
        topvbox.setSpacing(self.spacingHint())
        self.setMainWidget(topvbox)

        detailspace = QWidget(topvbox)

        # Info about the group.
        editgrid = QGridLayout(detailspace)
        editgrid.setSpacing(self.spacingHint())

        label = QLabel(i18n("Group Name:"),detailspace)
        editgrid.addWidget(label,0,0)
        self.groupnamelabel = KLineEdit("",detailspace)
        self.groupnamelabel.setReadOnly(True)
        editgrid.addWidget(self.groupnamelabel,0,1)

        label = QLabel(i18n("Group ID:"),detailspace)
        editgrid.addWidget(label,1,0)
        self.groupidlabel = KLineEdit("",detailspace)
        self.groupidlabel.setReadOnly(True)
        editgrid.addWidget(self.groupidlabel,1,1)

        # Available Groups
        tophbox = KHBox(topvbox)
        tophbox.setSpacing(self.spacingHint())

        hbox = tophbox

        vbox = KVBox(hbox)
        vbox.setSpacing(self.spacingHint())
        hbox.setStretchFactor(vbox,1)
        label = QLabel(i18n("Available Accounts"),vbox)
        vbox.setStretchFactor(label,0)
        self.availablelist = KListWidget(vbox)
        vbox.setStretchFactor(self.availablelist,1)
        self.availablelist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.availablelist.setSelectionBehavior(QAbstractItemView.SelectRows)

        # ->, <- Buttons
        vbox = KVBox(hbox)
        vbox.setSpacing(self.spacingHint())
        hbox.setStretchFactor(vbox,0)
        spacer = QWidget(vbox);
        vbox.setStretchFactor(spacer,1)
        self.addbutton = KPushButton(i18n("Add ->"),vbox)
        self.connect(self.addbutton,SIGNAL("clicked()"),self.slotAddClicked)
        vbox.setStretchFactor(self.addbutton,0)
        self.removebutton = KPushButton(i18n("<- Remove"),vbox)
        self.connect(self.removebutton,SIGNAL("clicked()"),self.slotRemoveClicked)
        vbox.setStretchFactor(self.removebutton,0)
        spacer = QWidget(vbox);
        vbox.setStretchFactor(spacer,1)

        # Selected Groups
        vbox = KVBox(hbox)
        vbox.setSpacing(self.spacingHint())
        hbox.setStretchFactor(vbox,1)
        label = QLabel(i18n("Selected Accounts"),vbox)
        vbox.setStretchFactor(label,0)
        self.selectedlist = KListWidget(vbox)
        vbox.setStretchFactor(self.selectedlist,1)
        self.selectedlist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.selectedlist.setSelectionBehavior(QAbstractItemView.SelectRows)

    #######################################################################
    def showEditGroup(self,groupid):
        self.groupid = groupid
        self.newgroupmode = False

        groupobj = self.admincontext.lookupGID(groupid)

        self.groupnamelabel.setText(groupobj.getGroupname())
        self.groupidlabel.setText(unicode(groupid))

        availablemembers = [u.getUsername() for u in self.admincontext.getUsers()]
        originalmembers = [u.getUsername() for u in groupobj.getUsers()]

        self.__updateLists(availablemembers,originalmembers)

        if self.exec_()==QDialog.Accepted:
            newmembers = []
            for i in range(self.selectedlist.count()):
                newmembers.append(unicode(self.selectedlist.item(i).text()))

            # Remove from the group object any unselected users.
            for member in originalmembers:
                if u not in newmembers:
                    self.admincontext.lookupUsername(member).removeFromGroup(groupobj)
            # Put the additional members in the group
            for member in newmembers:
                self.admincontext.lookupUsername(member).addToGroup(groupobj)
            self.admincontext.save()
            return True
        else:
            return False

    #######################################################################
    def showNewGroup(self):
        self.updatingGUI = True
        self.newgroupmode = True

        groupname = self.__fudgeNewGroupName(i18n("<Base string for creating new group names>","new_group"))

        self.groupobj = self.admincontext.newGroup(True)
        self.groupobj.setGroupname(groupname)

        groupname = self.groupobj.getGroupname()
        self.groupnamelabel.setText(groupname)
        self.groupnamelabel.setReadOnly(False)
        self.groupidlabel.setText(unicode(self.groupobj.getGID()))
        self.groupidlabel.setReadOnly(False)

        availablemembers = [u.getUsername() for u in self.admincontext.getUsers()]

        self.__updateLists(availablemembers,[])

        if self.exec_()==QDialog.Accepted:
            self.groupobj.setGroupname(unicode(self.groupnamelabel.text()))
            newgroupid = int(unicode(self.groupidlabel.text()))
            self.groupobj.setGID(newgroupid)

            newmembers = []
            for i in range(self.selectedlist.count()):
                newmembers.append(unicode(self.selectedlist.item(i).text()))

            self.admincontext.addGroup(self.groupobj)

            # Put the additional members in the group
            for member in newmembers:
                self.admincontext.lookupUsername(member).addToGroup(self.groupobj)
            self.admincontext.save()

            return newgroupid
        else:
            return None

    #######################################################################
    def slotAddClicked(self):
        item = self.availablelist.currentItem()
        if item!=None:
            self.selectedlist.addItem(item.text())
            self.availablelist.takeItem(self.availablelist.row(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.currentItem()==None)
            self.removebutton.setDisabled(self.selectedlist.currentItem()==None)

    #######################################################################
    def slotRemoveClicked(self):
        item = self.selectedlist.currentItem()
        if item!=None:
            self.availablelist.addItem(item.text())
            self.selectedlist.takeItem(self.selectedlist.row(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.currentItem()==None)
            self.removebutton.setDisabled(self.selectedlist.currentItem()==None)

    #######################################################################
    def __updateLists(self,grouplist,selectedlist):
        self.selectedlist.clear()
        for item in selectedlist:
            self.selectedlist.addItem(item)
        self.selectedlist.sortItems()

        self.availablelist.clear()
        for item in grouplist:
            if item not in selectedlist:
                self.availablelist.addItem(item)
        self.availablelist.sortItems()

        self._selectFirstAvailable()
        self.addbutton.setDisabled(self.availablelist.currentItem()==None)

        self._selectFirstSelected()
        self.removebutton.setDisabled(self.selectedlist.currentItem()==None)

    #######################################################################
    def _selectFirstAvailable(self):
        if self.availablelist.count()!=0:
            if self.availablelist.currentItem()==None:
                self.availablelist.setCurrentRow(0)

    #######################################################################
    def _selectFirstSelected(self):
        if self.selectedlist.count()!=0:
            if self.selectedlist.currentItem()==None:
                self.selectedlist.setCurrentRow(0)

    #######################################################################
    def __fudgeNewGroupName(self,basename):
        availablegroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        if basename not in availablegroups:
            return basename
        x = 1
        while basename + u'_' + unicode(x) in availablegroups:
            x += 1
        return basename + u'_' + unicode(x)

