#!/usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
##
## Copyright 2003-2006 Simon Edwards <simon@simonzone.com>
## Copyright 2008-2009 Yuriy Kozlov <yuriy-kozlov@kubuntu.org>
## Copyright 2008-2009 Jonathan Thomas <echidnaman@kubuntu.org>,
## Copyright 2008-2009 Ralph Janke <txwikinger@ubuntu.com>
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

# Qt imports
from PyQt4.QtGui import *
from PyQt4.QtCore import *

# KDE imports
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *

import locale

class GroupEditDialog(KDialog):
    def __init__(self,parent,admincontext):
        KDialog.__init__(self, parent)
        self.setModal(True)
        self.setCaption(i18n("Edit Group"))
        
        self.admincontext = admincontext
        self.groupobj = None
        
        self.updatingGUI = True

        # TODO: Port this to designer
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
        self.groupidlabel.setValidator(
                        QIntValidator(0, 65535, self.groupidlabel))

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
        self.addbutton = KPushButton(i18n("Add"), vbox)
        self.addbutton.setIcon(KIcon('arrow-right'))
        self.connect(self.addbutton,SIGNAL("clicked()"),self.slotAddClicked)
        vbox.setStretchFactor(self.addbutton,0)
        self.removebutton = KPushButton(i18n("Remove"), vbox)
        self.removebutton.setIcon(KIcon('arrow-left'))
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
        
        # Data changed signals
        self.connect(self.selectedlist.model(),
                     SIGNAL("rowsInserted(const QModelIndex&,int,int)"),
                     self.slotDataChanged)
        self.connect(self.selectedlist.model(),
                     SIGNAL("rowsRemoved(const QModelIndex&,int,int)"),
                     self.slotDataChanged)
        
        self.updatingGUI = False

    #######################################################################
    def showEditGroup(self, groupid):
        """ Sets up the dialog to modify an existing group.
            Returns the GID of the group if successful, None otherwise.
        """
        self.updatingGUI = True
        self.newgroupmode = False
        self.groupobj = self.admincontext.lookupGID(groupid)
        self.setCaption(i18n("Modifying Group %1")\
                            .arg(self.groupobj.getGroupname()))
        # Set up buttons
        self.setButtons(KDialog.ButtonCode(KDialog.Cancel | KDialog.Ok |
                                           KDialog.Apply))
        self.connect(self, SIGNAL("applyClicked()"), self.applyChanges)

        self.groupnamelabel.setText(self.groupobj.getGroupname())
        self.groupnamelabel.setReadOnly(True)
        self.groupidlabel.setText(unicode(groupid))
        self.groupidlabel.setReadOnly(True)

        availablemembers = [u.getUsername()
                                for u in self.admincontext.getUsers()]
        self.originalmembers = [u.getUsername()
                                    for u in self.groupobj.getUsers()]
        self.originalmembers.sort()

        # Works, not worth porting to Model/View
        self.__updateLists(availablemembers, self.originalmembers)
        
        self.slotDataChanged()

        self.updatingGUI = False
        
        if self.exec_() == QDialog.Accepted:
            result = self.applyChanges()
            if result:
                return self.groupobj.getGID()
            else:
                return None
        else:
            return None

    #######################################################################
    def showNewGroup(self):
        """ Sets up the dialog to create a new group.
            Returns the GID of the new group if successful, None otherwise.
        """
        self.updatingGUI = True
        self.newgroupmode = True
        self.setCaption(i18n("New Group"))
        # Set up buttons
        self.setButtons(KDialog.ButtonCode(KDialog.Cancel | KDialog.Ok))
        
        self.groupobj = self.admincontext.newGroup(True)
        
        groupname = self.__fudgeNewGroupName(i18n("<Base string for creating new group names>","new_group"))
        groupname = self.__fudgeNewGroupName(i18n("new_group","new_group"))
        
        # Populate group data from autogenerated
        self.groupobj.setGroupname(groupname)

        # Populate GUI
        groupname = self.groupobj.getGroupname()
        self.groupnamelabel.setText(groupname)
        self.groupnamelabel.setReadOnly(False)
        self.groupidlabel.setText(unicode(self.groupobj.getGID()))
        self.groupidlabel.setReadOnly(False)

        availablemembers = [u.getUsername()
                                for u in self.admincontext.getUsers()]

        self.__updateLists(availablemembers,[])
        
        self.updatingGUI = False

        if self.exec_() == QDialog.Accepted:
            # Populate group data from GUI
            self.groupobj.setGroupname(unicode(self.groupnamelabel.text()))
            newgroupid = int(unicode(self.groupidlabel.text()))
            self.groupobj.setGID(newgroupid)

            result = self.applyChanges()
            if result:
                return self.groupobj.getGID()
            else:
                return None
        else:
            return None

    ########################################################################
    def sanityCheck(self):
        """ Do some sanity checks.
            Returns True if data is ok or has been fixed up, otherwise pops up
            a message and returns False
        """
        # Check that the username doesn't clash
        # TODO: do this in the UI instead of canceling the operation
        newgroupname = unicode(self.groupnamelabel.text())
        existinggroup = self.admincontext.lookupGroupname(newgroupname)
        if existinggroup is not None and existinggroup is not self.groupobj:
            KMessageBox.sorry(self, i18n("Sorry, you must choose a different " +
                                         "group name.\n" +
                                         "'%1' is already being used.")\
                                         .arg(newgroupname))
            return False
        
        # Check that the UID doesn't clash (can't change GID of existing group)
        # TODO: do this in the UI instead of canceling the operation
        if self.newgroupmode:
            newgid = int(unicode(self.groupidlabel.text()))
            originalgid = self.groupobj.getGID()
            if self.admincontext.lookupGID(newgid) is not None:
                rc = KMessageBox.questionYesNo(self,
                        i18n("Sorry, the GID %1 is already in use. Should %2" +
                             " be used instead?").arg(newgid).arg(originalgid),
                        i18n("Group ID in use"))
                if rc == KMessageBox.Yes:
                    self.groupidlabel.setValue(unicode(originalgid))
                else:
                    return False
        
        return True
    
    ########################################################################
    def applyChanges(self):
        if not self.newgroupmode and not self.isChanged():
            return False
        
        if not self.sanityCheck():
            return False
        
        newmembers = []
        for i in range(self.selectedlist.count()):
            newmembers.append(unicode(self.selectedlist.item(i).text()))

        if self.newgroupmode:
            self.admincontext.addGroup(self.groupobj)
        else:
            # Remove from the group object any unselected users.
            for member in self.originalmembers:
                if member not in newmembers:
                    self.admincontext.lookupUsername(member)\
                            .removeFromGroup(self.groupobj)

        # Put the additional members in the group
        for member in newmembers:
            self.admincontext.lookupUsername(member).addToGroup(self.groupobj)
        
        # Save everything
        self.admincontext.save()
        
        # For the apply button
        self.originalmembers = [u.getUsername()
                                    for u in self.groupobj.getUsers()]
        self.originalmembers.sort()
        self.slotDataChanged()
        
        return True
    
    ########################################################################
    def isChanged(self):
        if not self.newgroupmode:
            newmembers = []
            for i in range(self.selectedlist.count()):
                newmembers.append(unicode(self.selectedlist.item(i).text()))
            newmembers.sort()
            changed = newmembers != self.originalmembers
            return changed
        else:
            return False
    
    ########################################################################
    def slotDataChanged(self):
        changed = self.isChanged()
        
        if not self.newgroupmode:
            self.enableButtonOk(changed)
            self.enableButtonApply(changed)
            self.setCaption(i18n("Modifying Group %1")\
                            .arg(self.groupobj.getGroupname()),
                            changed)
    
    #######################################################################
    def slotAddClicked(self):
        item = self.availablelist.currentItem()
        if item is not None:
            self.selectedlist.addItem(item.text())
            self.availablelist.takeItem(self.availablelist.row(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.currentItem()==None)
            self.removebutton.setDisabled(self.selectedlist.currentItem()==None)

    #######################################################################
    def slotRemoveClicked(self):
        item = self.selectedlist.currentItem()
        if item is not None:
            self.availablelist.addItem(item.text())
            self.selectedlist.takeItem(self.selectedlist.row(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.currentItem()==None)
            self.removebutton.setDisabled(self.selectedlist.currentItem()==None)

    #######################################################################
    def __updateLists(self, grouplist, selectedlist):
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
        self.addbutton.setDisabled(self.availablelist.currentItem() == None)

        self._selectFirstSelected()
        self.removebutton.setDisabled(self.selectedlist.currentItem() == None)

    #######################################################################
    def _selectFirstAvailable(self):
        if self.availablelist.count() != 0:
            if self.availablelist.currentItem() is None:
                self.availablelist.setCurrentRow(0)

    #######################################################################
    def _selectFirstSelected(self):
        if self.selectedlist.count()!=0:
            if self.selectedlist.currentItem() is None:
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

