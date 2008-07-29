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

#from qt import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *
#from kdeui import *
#from kdecore import *
#from kfile import *
from PyKDE4.kdecore import *
from PyKDE4.kdeui import *
from PyKDE4.kio import *
import sys
import os.path
import shutil
from util import unixauthdb
from util.groups import *   # TODO: Get rid of * imports
from user import UserEditDialog, UserDeleteDialog
from group import GroupEditDialog
import locale

programname = "userconfig"
version = "0.8.0"
# Are we running as a separate standalone application or in KControl?
standalone = __name__=='__main__'

# Running as the root user or not?
isroot = os.getuid()==0
#isroot = True

###########################################################################
def SptimeToQDate(sptime):
    t = QDateTime()
    t.setTime_t(0)
    return t.addDays(sptime).date()

###########################################################################
def QDateToSptime(qdate):
    x = QDateTime()
    x.setTime_t(0)
    return x.daysTo(QDateTime(qdate))

###########################################################################
# Try translating this code to C++. I dare ya!
if standalone:
    programbase = KPageDialog
else:
    programbase = KCModule

class UserConfigApp(programbase):
    def __init__(self,parent=None,name=None):
        global standalone,isroot
        KGlobal.locale().insertCatalog("guidance")

        if standalone:
            #KDialogBase.__init__(self,KJanusWidget.Tabbed,i18n("User Accounts and Groups"),
                #KDialogBase.User1|KDialogBase.Close, KDialogBase.Close)
            #self.setButtonText(KDialogBase.User1,i18n("About"))
            KPageDialog.__init__( self, parent )
            self.setFaceType( KPageDialog.Tabbed )
            #self.setObjectName( name )
            #self.setModal( modal )
            self.setCaption( i18n( "User Accounts and Groups" ) )
            #self.setButtons( KDialog.User1|KDialog.Close) #TODO
        else:
            KCModule.__init__(self,parent,name)
            self.setButtons(0)
            self.aboutdata = MakeAboutData()

            toplayout = KVBoxLayout( self, 0, KDialog.spacingHint() )
            tabcontrol = QTabWidget(self)
            toplayout.addWidget(tabcontrol)
            toplayout.setStretchFactor(tabcontrol,1)

        # Create a configuration object.
        self.config = KConfig("userconfigrc")

        KIconLoader.global_().addAppDir("guidance")

        self.usersToListItems = None
        self.selecteduserid = None
        self.selectedgroupid = None
        self.showsystemaccounts = False
        self.showsystemgroups = False

        self.updatingGUI = True


        #self.aboutus = KAboutApplicationDialog(self) #TODO

        # --- User Tab ---
        if standalone:
            usershbox = KHBox(self)
            item = self.addPage( usershbox, i18n( "Users" ) )
            item.setHeader( i18n( "Users" ) )
            vbox = KVBox(usershbox)
        else:
            vbox = KVBox(tabcontrol)
            vbox.setMargin(KDialog.marginHint())

        vbox.setSpacing(KDialog.spacingHint())

        hb = KHBox(vbox)
        hb.setSpacing(KDialog.spacingHint())
        vbox.setStretchFactor(hb,0)

        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-user"))
        hb.setStretchFactor(label,0)

        label = QLabel(i18n("User Accounts:"),hb)
        hb.setStretchFactor(label,1)

        self.userlist = QTreeWidget(vbox)
        #self.userlist.addColumn(i18n("Login Name"))
        #self.userlist.addColumn(i18n("Real Name"))
        #self.userlist.addColumn(i18n("UID"))
        self.userlist.setColumnCount( 3 )
        self.userlist.setAllColumnsShowFocus(True)
        self.userlist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.userlist.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.connect(self.userlist, SIGNAL("selectionChanged(QListViewItem *)"), self.slotListClicked)
        if isroot:
            self.connect(self.userlist, SIGNAL("doubleClicked(QListViewItem *)"), self.slotModifyClicked)
        self.connect(self.userlist, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), self.slotUserContext)

        self.showspecialcheckbox = QCheckBox(i18n("Show system accounts"),vbox)
        vbox.setStretchFactor(self.showspecialcheckbox,0)
        self.connect(self.showspecialcheckbox,SIGNAL("toggled(bool)"), self.slotShowSystemToggled)

        hbox = KHBox(vbox)
        hbox.setSpacing(KDialog.spacingHint())

        vbox.setStretchFactor(hbox,0)

        self.modifybutton = KPushButton(i18n("Modify..."),hbox)
        hbox.setStretchFactor(self.modifybutton,1)
        self.connect(self.modifybutton,SIGNAL("clicked()"),self.slotModifyClicked)

        self.newbutton = KPushButton(i18n("New..."),hbox)
        hbox.setStretchFactor(self.newbutton,1)
        self.connect(self.newbutton,SIGNAL("clicked()"),self.slotNewClicked)

        self.deletebutton = KPushButton(i18n("Delete..."),hbox)
        hbox.setStretchFactor(self.deletebutton,1)
        self.connect(self.deletebutton,SIGNAL("clicked()"),self.slotDeleteClicked)

        detailsgroupbox = QGroupBox(i18n("Details"),vbox)
        detailsbox = KVBox( detailsgroupbox )
        userinfovbox = QWidget(detailsbox)

        infogrid = QGridLayout(userinfovbox)
        infogrid.setSpacing(KDialog.spacingHint())

        label = QLabel(i18n("Login Name:"),userinfovbox)
        infogrid.addWidget(label,0,0)
        self.loginnamelabel = KLineEdit("",userinfovbox)
        self.loginnamelabel.setReadOnly(True)
        infogrid.addWidget(self.loginnamelabel,0,1)

        label = QLabel(i18n("Real Name:"),userinfovbox)
        infogrid.addWidget(label,0,2)
        self.realnamelabel = KLineEdit("",userinfovbox)
        self.realnamelabel.setReadOnly(True)
        infogrid.addWidget(self.realnamelabel,0,3)

        label = QLabel(i18n("UID:"),userinfovbox)
        infogrid.addWidget(label,1,0)
        self.uidlabel = KLineEdit("",userinfovbox)
        self.uidlabel.setReadOnly(True)
        infogrid.addWidget(self.uidlabel,1,1)

        label = QLabel(i18n("Status:"),userinfovbox)
        infogrid.addWidget(label,1,2)
        self.statuslabel = KLineEdit("",userinfovbox)
        self.statuslabel.setReadOnly(True)
        infogrid.addWidget(self.statuslabel,1,3)

        label = QLabel(i18n("Primary Group:"),userinfovbox)
        infogrid.addWidget(label,2,0)
        self.primarygrouplabel = KLineEdit("",userinfovbox)
        self.primarygrouplabel.setReadOnly(True)
        infogrid.addWidget(self.primarygrouplabel,2,1)

        label = QLabel(i18n("Secondary Groups:"),userinfovbox)
        infogrid.addWidget(label,2,2)
        self.secondarygrouplabel = KLineEdit("",userinfovbox)
        self.secondarygrouplabel.setReadOnly(True)
        infogrid.addWidget(self.secondarygrouplabel,2,3)

        if not standalone:
            tabcontrol.addTab(vbox,i18n("Users"))

        #--- Groups Tab ---
        if standalone:
            groupsvbox = KVBox(self)
            item = self.addPage( groupsvbox, i18n( "Groups" ) )
            item.setHeader( i18n( "Groups" ) )
            hb = KHBox(groupsvbox)
        else:
            groupsvbox = KVBox(tabcontrol)
            groupsvbox.setMargin(KDialog.marginHint())
            hb = KHBox(groupsvbox)

        topframe = QFrame(groupsvbox)
        groupsvbox.setSpacing(KDialog.spacingHint())
        hb.setSpacing(KDialog.spacingHint())
        groupsvbox.setStretchFactor(hb,0)

        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-group"))
        hb.setStretchFactor(label,0)

        label = QLabel(i18n("Groups:"),hb)
        hb.setStretchFactor(label,1)

        groupsplitter = QSplitter(Qt.Vertical,groupsvbox)
        
        self.grouplist = QTreeWidget(groupsplitter)
        #self.grouplist.addColumn(i18n("Group Name"))
        #self.grouplist.addColumn(i18n("GID"))
        self.userlist.setColumnCount( 2 )
        self.grouplist.setAllColumnsShowFocus(True)
        self.grouplist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grouplist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.connect(self.grouplist, SIGNAL("selectionChanged(QListViewItem *)"), self.slotGroupListClicked)

        if isroot:
            self.connect(self.grouplist, SIGNAL("doubleClicked(QListViewItem *)"), self.slotModifyGroupClicked)
        self.connect(self.grouplist, SIGNAL("contextMenu(KListView*,QListViewItem*,const QPoint&)"), 
                self.slotGroupContext)

        groupbottomvbox = KVBox(groupsplitter)
        groupbottomvbox.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)

        self.showspecialgroupscheckbox = QCheckBox(i18n("Show system groups"),groupbottomvbox)
        vbox.setStretchFactor(self.showspecialgroupscheckbox,0)
        self.connect(self.showspecialgroupscheckbox,SIGNAL("toggled(bool)"), self.slotShowSystemGroupsToggled)

        hbox = KHBox(groupbottomvbox)
        hbox.setSpacing(KDialog.spacingHint())

        groupsvbox.setStretchFactor(hbox,0)

        self.modifygroupbutton = KPushButton(i18n("Modify..."),hbox)
        hbox.setStretchFactor(self.modifygroupbutton,1)
        self.connect(self.modifygroupbutton,SIGNAL("clicked()"),self.slotModifyGroupClicked)

        self.newgroupbutton = KPushButton(i18n("New..."),hbox)
        hbox.setStretchFactor(self.newgroupbutton,1)
        self.connect(self.newgroupbutton,SIGNAL("clicked()"),self.slotNewGroupClicked)

        self.deletegroupbutton = KPushButton(i18n("Delete..."),hbox)
        hbox.setStretchFactor(self.deletegroupbutton,1)
        self.connect(self.deletegroupbutton,SIGNAL("clicked()"),self.slotDeleteGroupClicked)

        if not isroot:
            disablebuttons = (  self.modifybutton, self.modifygroupbutton, self.deletebutton, self.deletegroupbutton,
                                self.newbutton, self.newgroupbutton)
            for widget in disablebuttons:
                widget.setDisabled(True)

        label = QLabel(i18n("Group Members:"),groupbottomvbox)
        groupsvbox.setStretchFactor(label,0)

        self.groupmemberlist = QTreeWidget(groupbottomvbox)
        #self.groupmemberlist.addColumn(i18n("Login Name"))
        #self.groupmemberlist.addColumn(i18n("Real Name"))
        #self.groupmemberlist.addColumn(i18n("UID"))
        self.groupmemberlist.setColumnCount( 3 )
        self.groupmemberlist.setAllColumnsShowFocus(True)
        self.groupmemberlist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.groupmemberlist.setSelectionBehavior(QAbstractItemView.SelectRows)

        if not standalone:
            tabcontrol.addTab(groupsvbox,i18n("Groups"))

        self.admincontext = unixauthdb.getContext(isroot)

        self.updatingGUI = True

        self.showspecialcheckbox.setChecked(self.showsystemaccounts)
        self.showspecialgroupscheckbox.setChecked(self.showsystemgroups)

        self.__updateUserList()
        self.__updateGroupList()
        self.updatingGUI = False

        self.usereditdialog = UserEditDialog(None,self.admincontext)
        self.userdeletedialog = UserDeleteDialog(None,self.admincontext)
        self.groupeditdialog = GroupEditDialog(None,self.admincontext)

    #######################################################################
    def exec_(self):
        global programbase
        self.__loadOptions()
        self.updatingGUI = True
        self.__updateUserList()
        self.__updateGroupList()
        self.updatingGUI = False
        programbase.exec_(self)
        self.__saveOptions()

    #######################################################################
    def slotUser1(self):
        self.aboutus.show()

    #######################################################################
    def slotUserContext(self,l,v,p):
        cmenu = KPopupMenu(self,"MyActions")
        cmenu.insertItem(i18n("Modify..."), self.slotModifyClicked, 0, 0)
        cmenu.insertItem(i18n("Delete..."), self.slotDeleteClicked, 0, 1)
        if not isroot:
            cmenu.setItemEnabled(0,False)
            cmenu.setItemEnabled(1,False)

        cmenu.exec_(p)

    #######################################################################
    def slotGroupContext(self,l,v,p):
        cmenu = KPopupMenu(self,"MyActions")
        cmenu.insertItem(i18n("Modify..."), self.slotModifyGroupClicked, 0, 0)
        cmenu.insertItem(i18n("Delete..."), self.slotDeleteGroupClicked, 0, 1)
        if not isroot:
            cmenu.setItemEnabled(0,False)
            cmenu.setItemEnabled(1,False)
        cmenu.exec_(p)

    #######################################################################        
    def sizeHint(self):
        global programbase
        size_hint = programbase.sizeHint(self)
        # Just make the dialog a little shorter by default.
        size_hint.setHeight(size_hint.height()-200) 
        return size_hint

    #######################################################################
    def slotCloseButton(self):
        self.close()

    #######################################################################
    def slotListClicked(self,item):
        if self.updatingGUI==False:
            for userid in self.useridsToListItems:
                if self.useridsToListItems[userid]==item:
                    self.updatingGUI = True
                    self.__selectUser(userid)
                    self.updatingGUI = False
                    return

    #######################################################################
    def slotShowSystemToggled(self,on):
        self.showsystemaccounts = on
        if self.updatingGUI==False:
            self.updatingGUI = True
            self.__updateUserList()
            self.updatingGUI = False

    #######################################################################
    def slotModifyClicked(self):
        self.usereditdialog.showEditUser(self.selecteduserid)
        self.updatingGUI = True
        self.__updateUser(self.selecteduserid)
        self.__selectUser(self.selecteduserid)
        self.updatingGUI = False

    #######################################################################
    def slotNewClicked(self):
        newuid = self.usereditdialog.showNewUser()
        if newuid!=None:
            self.updatingGUI = True
            self.__updateUserList()
            self.__selectUser(newuid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteClicked(self):
        if self.userdeletedialog.deleteUser(self.selecteduserid):
            self.updatingGUI = True
            self.selecteduserid = None
            self.__updateUserList()
            self.updatingGUI = False

    #######################################################################
    def slotGroupListClicked(self,item):
        if self.updatingGUI==False:
            for groupid in self.groupidsToListItems:
                if groupid and self.groupidsToListItems[groupid]==item:
                    self.updatingGUI = True
                    self.__selectGroup(groupid)
                    self.updatingGUI = False
                    return

    #######################################################################
    def slotShowSystemGroupsToggled(self,on):
        self.showsystemgroups = on
        if self.updatingGUI==False:
            self.updatingGUI = True
            self.__updateGroupList()
            self.updatingGUI = False

    #######################################################################
    def slotModifyGroupClicked(self):
        if self.selectedgroupid!=None:
            if self.groupeditdialog.showEditGroup(self.selectedgroupid):
                self.__selectGroup(self.selectedgroupid)
                self.updatingGUI = True
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def slotNewGroupClicked(self):
        newgroupid = self.groupeditdialog.showNewGroup()
        if newgroupid!=None:
            self.updatingGUI = True
            self.__updateGroupList()
            self.__updateGroupList()
            self.__selectGroup(newgroupid)
            self.__updateUser(self.selecteduserid)
            self.__selectUser(self.selecteduserid)
            self.updatingGUI = False

    #######################################################################
    def slotDeleteGroupClicked(self):
        if self.selectedgroupid!=None:
            groupobj = self.admincontext.lookupGID(self.selectedgroupid)
            groupname = groupobj.getGroupname()
            gid = groupobj.getGID()
            nummembers = len(groupobj.getUsers())

            message = i18n("Are you sure you want to delete group '%1' (%2)?\nIt currently has %3 members.").arg(groupname).arg(gid).arg(nummembers)
            if KMessageBox.warningYesNo(self,message,i18n("Delete Group?"))==KMessageBox.Yes:
                self.admincontext.removeGroup(groupobj)
                self.admincontext.save()
                self.updatingGUI = True
                self.__updateGroupList()
                self.__updateUser(self.selecteduserid)
                self.__selectUser(self.selecteduserid)
                self.updatingGUI = False

    #######################################################################
    def __updateUserList(self):
        self.userlist.clear()
        self.useridsToListItems = {}
        firstselecteduserid = None

        users = self.admincontext.getUsers()

        for userobj in users:
            uid = userobj.getUID()
            if self.showsystemaccounts or not userobj.isSystemUser():
                itemstrings = QStringList()
                itemstrings.append(userobj.getUsername())
                itemstrings.append(userobj.getRealName())
                itemstrings.append(unicode(uid))
                lvi = QTreeWidgetItem(self.userlist,itemstrings)
                if userobj.isLocked():
                    lvi.setPixmap(0,UserIcon("hi16-encrypted"))
                self.useridsToListItems[uid] = lvi
                if self.selecteduserid==uid:
                    firstselecteduserid = uid
                elif firstselecteduserid==None:
                    firstselecteduserid = uid
        self.selecteduserid = firstselecteduserid
        self.__selectUser(self.selecteduserid)
        #self.userlist.ensureItemVisible(self.userlist.currentItem())

    #######################################################################
    def __updateUser(self,userid):
        lvi = self.useridsToListItems[userid]
        userobj = self.admincontext.lookupUID(userid)
        lvi.setText(0,userobj.getUsername())
        lvi.setText(1,userobj.getRealName())
        lvi.setText(2,unicode(userobj.getUID()))
        if userobj.isLocked():
            lvi.setPixmap(0,UserIcon("hi16-encrypted"))
        else:
            lvi.setPixmap(0,QPixmap())

    #######################################################################
    def __selectUser(self,userid):
        self.selecteduserid = userid
        # Only go on if there are actual users.
        if len(self.useridsToListItems)>0:
            lvi = self.useridsToListItems[userid]
            #self.userlist.setSelected(lvi,True)
            self.userlist.setCurrentItem(lvi)

            userobj = self.admincontext.lookupUID(userid)

            username = userobj.getUsername()
            self.loginnamelabel.setText(username)
            self.realnamelabel.setText(userobj.getRealName())
            self.uidlabel.setText(unicode(userid))
            if userobj.isLocked():
                self.statuslabel.setText(i18n("Disabled"))
            else:
                self.statuslabel.setText(i18n("Enabled"))

            # Primary Group
            primarygroupobj = userobj.getPrimaryGroup()
            primarygroupname = primarygroupobj.getGroupname()
            self.primarygrouplabel.setText(primarygroupname)

            # Secondary Groups
            secondarygroups = [g.getGroupname() for g in userobj.getGroups() if g is not userobj.getPrimaryGroup()]
            self.secondarygrouplabel.setText(unicode(i18n(", ")).join(secondarygroups))

            if isroot:
                self.deletebutton.setDisabled(userobj.getUID()==0)

    #######################################################################
    def __updateGroupList(self):
        self.grouplist.clear()
        self.groupidsToListItems = {}
        firstselectedgroupid = None

        groups = self.admincontext.getGroups()
        for groupobj in groups:
            gid = groupobj.getGID()
            if self.showsystemgroups or not groupobj.isSystemGroup():
                itemstrings = QStringList()
                itemstrings.append(groupobj.getGroupname())
                itemstrings.append(unicode(gid))
                lvi = QTreeWidgetItem(self.grouplist,itemstrings)
                self.groupidsToListItems[gid] = lvi
                if self.selectedgroupid==gid:
                    firstselectedgroupid = gid
                elif firstselectedgroupid==None:
                    firstselectedgroupid = gid
        self.selectedgroupid = firstselectedgroupid
        self.__selectGroup(self.selectedgroupid)
        #self.grouplist.ensureItemVisible(self.grouplist.currentItem())

    #######################################################################
    def __selectGroup(self,groupid):
        if groupid:
            self.selectedgroupid = groupid
            lvi = self.groupidsToListItems[groupid]
            #self.grouplist.setSelected(lvi,True)
            self.grouplist.setCurrentItem(lvi)

            groupobj = self.admincontext.lookupGID(groupid)
            members = groupobj.getUsers()
            self.groupmemberlist.clear()
            for userobj in members:
                if userobj!=None:
                    itemstrings = QStringList()
                    itemstrings.append(userobj.getUsername())
                    itemstrings.append(userobj.getRealName())
                    itemstrings.append(unicode(userobj.getUID()))
                    lvi = QTreeWidgetItem(self.groupmemberlist,itemstrings)
            if isroot:
                self.deletegroupbutton.setDisabled(groupobj.getGID()==0)

    #######################################################################
    def __loadOptions(self):
        #self.config.setGroup("General")
        
        size = self.config.group("General").readEntry("Geometry")
        #if size.isEmpty()==False:
            #self.resize(size)  # TODO
        #self.config.setGroup("Options")
        self.showsystemaccounts = self.config.group("Options").readEntry("ShowSystemAccounts")
        self.showspecialcheckbox.setChecked(bool(self.showsystemaccounts))
        self.showsystemgroups = self.config.group("Options").readEntry("ShowSystemGroups")
        self.showspecialgroupscheckbox.setChecked(bool(self.showsystemgroups))

    #######################################################################
    def __saveOptions(self):
        global isroot
        if isroot:
            return
        #self.config.setGroup("General")
        #self.config.group("General").writeEntry("Geometry", self.size())   # TODO
        #self.config.setGroup("Options")
        self.config.group("Options").writeEntry("ShowSystemAccounts",str(int(self.showsystemaccounts)))
        self.config.group("Options").writeEntry("ShowSystemGroups",str(int(self.showsystemgroups)))
        self.config.sync()

    #######################################################################
    # KControl virtual void methods
    def load(self):
        pass
    def save(self):
        pass
    def defaults(self):
        pass        
    def sysdefaults(self):
        pass

    def aboutData(self):
        # Return the KAboutData object which we created during initialisation.
        return self.aboutdata
    def buttons(self):
        # Only supply a Help button. Other choices are Default and Apply.
        return KCModule.Help

###########################################################################






###########################################################################
#class ListPickerDialog(KDialog):
    #def __init__(self,parent,caption,leftlabel,rightlabel):
        ##KDialogBase.__init__(self,parent,None,True,caption,KDialogBase.Ok|KDialogBase.Cancel, KDialogBase.Cancel)
        #KDialog.__init__(parent)
        #KDialog.setCaption(caption)
        #KDialog.setModal(True)
        #KDialog.setButtons(KDialog.Ok|KDialog.Cancel)

        #self.tophbox = KHBox(self)
        #self.setMainWidget(self.tophbox)
        #self.tophbox.setSpacing(self.spacingHint())
        ## Available Groups
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,1)
        #label = QLabel(leftlabel,vbox)
        #vbox.setStretchFactor(label,0)
        #self.availablelist = KListBox(vbox)
        #vbox.setStretchFactor(self.availablelist,1)

        ## ->, <- Buttons
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,0)
        #spacer = QWidget(vbox);
        #vbox.setStretchFactor(spacer,1)
        #self.addbutton = KPushButton(i18n("Add ->"),vbox)
        #self.connect(self.addbutton,SIGNAL("clicked()"),self.slotAddClicked)
        #vbox.setStretchFactor(self.addbutton,0)
        #self.removebutton = KPushButton(i18n("<- Remove"),vbox)
        #self.connect(self.removebutton,SIGNAL("clicked()"),self.slotRemoveClicked)
        #vbox.setStretchFactor(self.removebutton,0)
        #spacer = QWidget(vbox);
        #vbox.setStretchFactor(spacer,1)

        ## Selected Groups
        #vbox = KVBox(self.tophbox)
        #self.tophbox.setStretchFactor(vbox,1)
        #label = QLabel(rightlabel,vbox)
        #vbox.setStretchFactor(label,0)
        #self.selectedlist = KListBox(vbox)
        #vbox.setStretchFactor(self.selectedlist,1)

    ########################################################################
    #def do(self,grouplist,selectedlist):
        #self.selectedlist.clear()
        #for item in selectedlist:
            #self.selectedlist.insertItem(item)
        #self.selectedlist.sort()

        #self.availablelist.clear()
        #for item in grouplist:
            #if item not in selectedlist:
                #self.availablelist.insertItem(item)
        #self.availablelist.sort()

        #self._selectFirstAvailable()
        #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)

        #self._selectFirstSelected()
        #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

        #if self.exec_()==QDialog.Accepted:
            #newlist = []
            #for i in range(self.selectedlist.count()):
                #newlist.append(unicode(self.selectedlist.item(i).text()))
            #return newlist
        #else:
            #return selectedlist

    ########################################################################
    #def slotAddClicked(self):
        #item = self.availablelist.selectedItem()
        #if item!=None:
            #self.selectedlist.insertItem(item.text())
            #self.availablelist.removeItem(self.availablelist.index(item))
            #self._selectFirstAvailable()
            #self._selectFirstSelected()
            #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    ########################################################################
    #def slotRemoveClicked(self):
        #item = self.selectedlist.selectedItem()
        #if item!=None:
            #self.availablelist.insertItem(item.text())
            #self.selectedlist.removeItem(self.selectedlist.index(item))
            #self._selectFirstAvailable()
            #self._selectFirstSelected()
            #self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            #self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    ########################################################################
    #def _selectFirstAvailable(self):
        #if self.availablelist.count()!=0:
            #if self.availablelist.selectedItem()==None:
                #self.availablelist.setSelected(0,True)

    ########################################################################
    #def _selectFirstSelected(self):
        #if self.selectedlist.count()!=0:
            #if self.selectedlist.selectedItem()==None:
                #self.selectedlist.setSelected(0,True)

###########################################################################




############################################################################
# Factory function for KControl
def create_userconfig(parent,name):
    return UserConfigApp(parent, name)

##########################################################################
def MakeAboutData():
    aboutdata = KAboutData("guidance", "guidance", ki18n(programname), version,
        ki18n("User and Group Configuration Tool"),
        KAboutData.License_GPL, ki18n("Copyright (C) 2003-2007 Simon Edwards"))
    aboutdata.addAuthor(ki18n("Simon Edwards"), ki18n("Developer"), "simon@simonzone.com", "http://www.simonzone.com/software/")
    aboutdata.addAuthor(ki18n("Sebastian Kügler"), ki18n("Developer"), "sebas@kde.org", "http://vizZzion.org")
    return aboutdata

if standalone:
    aboutdata = MakeAboutData()

    KCmdLineArgs.init(sys.argv,aboutdata)

    kapp = KApplication()
    userconfigapp = UserConfigApp()
    userconfigapp.exec_()
