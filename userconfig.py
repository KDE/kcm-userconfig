#!/usr/bin/python
# -*- coding: UTF-8 -*-
###########################################################################
# userconfig.py - description                                             #
# ------------------------------                                          #
# begin     : Wed Apr 30 2003                                             #
# copyright : (C) 2003-2006 by Simon Edwards                              #
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
import unixauthdb
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

        #KIconLoader.global().addAppDir("guidance") #TODO

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

class UserEditDialog(KPageDialog):
    def __init__(self,parent,admincontext):
        #KDialogBase.__init__(self,KJanusWidget.Tabbed,i18n("User Account"),KDialogBase.Ok|KDialogBase.Cancel,
            #KDialogBase.Cancel,parent)
        KPageDialog.__init__( self, parent )
        self.setFaceType( KPageDialog.Tabbed )
        #self.setObjectName( name )
        self.setModal( True )
        self.setCaption( i18n( "User Account" ) )
        #self.setButtons( KDialog.Ok|KDialog.Cancel) # TODO

        self.admincontext = admincontext
        self.updatingGUI = True

        detailshbox = KHBox(self)
        item = self.addPage( detailshbox, i18n( "Details" ) )
        item.setHeader( i18n( "Details" ) )
        detailspace = QWidget(detailshbox)

        infogrid = QGridLayout(detailspace)
        infogrid.setSpacing(self.spacingHint())
        #infogrid.setColStretch(0,0)
        #infogrid.setColStretch(1,1)

        self.enabledradiogroup = QButtonGroup()
        #self.enabledradiogroup.setRadioButtonExclusive(True)
        hb = KHBox(detailspace)
        hb.setSpacing(self.spacingHint())
        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-identity"))
        hb.setStretchFactor(label,0)
        label = QLabel(i18n("Status:"),hb)
        hb.setStretchFactor(label,1)
        infogrid.addWidget(hb,0,1,0,0)

        self.enabledradio = QRadioButton(i18n("Enabled"),detailspace)
        infogrid.addWidget(self.enabledradio,0,1)

        hbox = KHBox(detailspace)
        hbox.setSpacing(self.spacingHint())
        self.disabledradio = QRadioButton(i18n("Disabled"),hbox)
        hbox.setStretchFactor(self.disabledradio,0)
        label = QLabel(hbox)
        label.setPixmap(UserIcon("hi16-encrypted"))
        hbox.setStretchFactor(label,1)        
        infogrid.addWidget(hbox,1,1)

        self.enabledradiogroup.addButton(self.enabledradio,0)
        self.enabledradiogroup.addButton(self.disabledradio,1)

        label = QLabel(i18n("Login Name:"),detailspace)
        infogrid.addWidget(label,2,0)
        self.loginnameedit = KLineEdit("",detailspace)
        self.loginnameedit.setValidator(LoginNameValidator(self.loginnameedit))

        infogrid.addWidget(self.loginnameedit,2,1)
        self.connect(self.loginnameedit, SIGNAL("textChanged(const QString &)"), self.slotLoginChanged)

        label = QLabel(i18n("Real Name:"),detailspace)
        infogrid.addWidget(label,3,0)
        self.realnameedit = KLineEdit("",detailspace)
        self.realnameedit.setValidator(RealUserNameValidator(self.realnameedit))

        infogrid.addWidget(self.realnameedit,3,1)

        label = QLabel(i18n("User ID:"),detailspace)
        infogrid.addWidget(label,4,0)
        self.uidedit = KLineEdit("",detailspace)
        self.uidedit.setValidator(QIntValidator(0,65535,detailspace))
        infogrid.addWidget(self.uidedit,4,1)

        label = QLabel(i18n("Primary Group:"),detailspace)
        infogrid.addWidget(label,5,0)
        self.primarygroupedit = KComboBox(False,detailspace)
        infogrid.addWidget(self.primarygroupedit,5,1)

        label = QLabel(i18n("Home Directory:"),detailspace)
        infogrid.addWidget(label,7,0)

        hbox = KHBox(detailspace)
        hbox.setSpacing(self.spacingHint())
        self.homediredit = KLineEdit("",hbox)
        hbox.setStretchFactor(self.homediredit,1)
        self.connect(self.homediredit, SIGNAL("textChanged(const QString &)"), self.slotHomeDirChanged)
        self.homedirbutton = KPushButton(i18n("Browse..."),hbox)
        hbox.setStretchFactor(self.homedirbutton,0)
        self.connect(self.homedirbutton,SIGNAL("clicked()"),self.slotBrowseHomeDirClicked)
        infogrid.addWidget(hbox,7,1)

        label = QLabel(i18n("Shell:"),detailspace)
        infogrid.addWidget(label,8,0)

        self.shelledit = KComboBox(True,detailspace)
        for shell in self.admincontext.getUserShells():
            self.shelledit.addItem(shell)
        infogrid.addWidget(self.shelledit,8,1)

        # Rudd-O rules.  Not so much, but enough to rule.
        # yeah it's not my finest hour, but it works like a charm over here.  Please feel free to clean up dead code that I commented
        # I extend my deepest thanks to the people that have worked hard to construct this tool in the first place.  I have no idea who the authors and contributors are, but it would make sense to have all the contributors listed on top of the file.
        # Privileges and groups tab
        groupshbox = KHBox(self)
        item = self.addPage( groupshbox, i18n( "Privileges and groups" ) )
        item.setHeader( i18n( "Privileges and groups" ) )

        # Rudd-O now here we create the widget that will hold the group listing, and fill it with the groups.
        self.privilegeslistview = QListView(groupshbox)
        #self.privilegeslistview.addColumn(i18n("Privilege"),-1)
        self.groupslistview = QListView(groupshbox)
        #self.groupslistview.addColumn(i18n("Secondary group"),-1)
        groupshbox.setStretchFactor(self.privilegeslistview,3)
        groupshbox.setStretchFactor(self.groupslistview,2)
    
        # Password and Security Tab.
        passwordvbox = KVBox(self)
        item = self.addPage( passwordvbox, i18n( "Password && Security" ))
        item.setHeader( i18n("Password && Security" ))

        passwordspace = QWidget(passwordvbox)
        passwordgrid = QGridLayout(passwordspace)
        passwordgrid.setSpacing(self.spacingHint())
        #passwordgrid.setColStretch(0,0)
        #passwordgrid.setColStretch(1,0)
        #passwordgrid.setColStretch(2,1)
        passwordvbox.setStretchFactor(passwordspace,0)

        hb = KHBox(passwordspace)
        hb.setSpacing(self.spacingHint())
        label = QLabel(hb)
        label.setPixmap(UserIcon("hi32-password"))
        hb.setStretchFactor(label,0)
        label = QLabel(i18n("Password:"),hb)
        hb.setStretchFactor(label,1)
        passwordgrid.addWidget(hb,0,0)

        self.passwordedit = KLineEdit(passwordspace)
        self.passwordedit.setPasswordMode(True)
        passwordgrid.addWidget(self.passwordedit,0,1)

        # Last Change
        label = QLabel(i18n("Last changed:"),passwordspace)
        passwordgrid.addWidget(label,1,0)
        self.lastchangelabel = KLineEdit("",passwordspace)
        self.lastchangelabel.setReadOnly(True)
        passwordgrid.addWidget(self.lastchangelabel,1,1)

        self.validradiogroup = QButtonGroup()
        #self.validradiogroup.setRadioButtonExclusive(True) # TODO

        # Valid until.
        label = QLabel(i18n("Valid until:"),passwordspace)
        passwordgrid.addWidget(label,2,0)
        self.validalwaysradio = QRadioButton(i18n("Always"),passwordspace)
        passwordgrid.addWidget(self.validalwaysradio,2,1)

        hbox = KHBox(passwordspace)
        hbox.setSpacing(self.spacingHint())
        self.expireradio = QRadioButton(hbox)
        hbox.setStretchFactor(self.expireradio,0)

        self.expiredate = KDateWidget(hbox)
        hbox.setStretchFactor(self.expiredate,1)
        passwordgrid.addWidget(hbox,3,1)

        self.validradiogroup.addButton(self.validalwaysradio,0)
        self.validradiogroup.addButton(self.expireradio,1)
        self.connect(self.validradiogroup,SIGNAL("clicked(int)"),self.slotValidUntilClicked)

        # Password Aging & Expiration.
        passwordaginggroup = QGroupBox(i18n("Password Aging"),passwordvbox)
        passwordagingbox = KVBox(passwordaginggroup)
        #passwordagingbox.setInsideSpacing(self.spacingHint())
        passwordvbox.setStretchFactor(passwordagingbox,0)

        passwordagingwidget = QWidget(passwordagingbox)

        passwordaginggrid = QGridLayout(passwordagingwidget)
        passwordaginggrid.setSpacing(self.spacingHint())

        # [*] Require new password after: [_____5 days]
        self.forcepasswordchangecheckbox = QCheckBox(passwordagingwidget)
        self.connect(self.forcepasswordchangecheckbox,SIGNAL("toggled(bool)"),self.slotForcePasswordChangeToggled)
        passwordaginggrid.addWidget(self.forcepasswordchangecheckbox,0,0)
        label = QLabel(i18n("Require new password after:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,0,1) 
        self.maximumpasswordedit = QSpinBox(passwordagingwidget)
        self.maximumpasswordedit.setSuffix(i18n(" days"))
        self.maximumpasswordedit.setMinimum(1)
        self.maximumpasswordedit.setMaximum(365*5)
        passwordaginggrid.addWidget(self.maximumpasswordedit,0,2)

        label = QLabel(i18n("Warn before password expires:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,1,1)
        self.warningedit = QSpinBox(passwordagingwidget)
        self.warningedit.setPrefix(i18n("After "))
        self.warningedit.setSuffix(i18n(" days"))
        self.warningedit.setMinimum(0)
        self.warningedit.setMaximum(365*5)
        self.warningedit.setSpecialValueText(i18n("Never"))
        passwordaginggrid.addWidget(self.warningedit,1,2)

        label = QLabel(i18n("Disable account after password expires:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,2,1)
        self.disableexpireedit = QSpinBox(passwordagingwidget)
        self.disableexpireedit.setPrefix(i18n("After "))
        self.disableexpireedit.setSuffix(i18n(" days"))
        self.disableexpireedit.setMinimum(0)
        self.disableexpireedit.setMaximum(365*5)
        self.disableexpireedit.setSpecialValueText(i18n("Never"))
        passwordaginggrid.addWidget(self.disableexpireedit,2,2)

        self.enforcepasswordminagecheckbox = QCheckBox(passwordagingwidget)
        self.connect(self.enforcepasswordminagecheckbox,SIGNAL("toggled(bool)"),self.slotEnforePasswordAgeToggled)
        passwordaginggrid.addWidget(self.enforcepasswordminagecheckbox,3,0)

        label = QLabel(i18n("Enforce minimum password age:"),passwordagingwidget)
        passwordaginggrid.addWidget(label,3,1)
        self.minimumpasswordedit = QSpinBox(passwordagingwidget)
        self.minimumpasswordedit.setSuffix(i18n(" days"))
        passwordaginggrid.addWidget(self.minimumpasswordedit,3,2)

        spacer = QWidget(passwordvbox)
        passwordvbox.setStretchFactor(spacer,1)

        self.homedirdialog = KDirSelectDialog(KUrl.fromPath("/"),True,self)
        self.createhomedirectorydialog = OverwriteHomeDirectoryDialog(None)
        self.updatingGUI = False

    def _repopulateGroupsPrivileges(self,excludegroups=None):
        # needs listviews to be constructed.  Expects a list of PwdGroups to be excluded
        
        # rehash everything
        self.privilegeslistview.clear()
        self.groupslistview.clear()
        self.secondarygroupcheckboxes = {}
        pn = PrivilegeNames()
        
        if excludegroups: excludegroups = [ g.getGroupname() for g in excludegroups ]
        else: excludegroups = []
        for group in [g.getGroupname() for g in self.admincontext.getGroups()]:
            if group in excludegroups: continue
            if group in pn:
                name = i18n(unicode(pn[group]).encode(locale.getpreferredencoding()))
                wid = self.privilegeslistview
            else:
                name = unicode(group).encode(locale.getpreferredencoding())
                wid = self.groupslistview
            self.secondarygroupcheckboxes[group] = QCheckListItem(wid,name,QCheckListItem.CheckBox)

    ########################################################################
    def showEditUser(self,userid):
        self.updatingGUI = True
        self.newusermode = False
        self.userobj = self.admincontext.lookupUID(userid)
        self.userid = userid
        self.passwordedit.erase()
        self.selectedgroups = [g.getGroupname() for g in self.userobj.getGroups()
            if g is not self.userobj.getPrimaryGroup()]
        
        # Rudd-O: now here we tick the appropriate group listing checkbox, and hide the currently active primary group of the user.  We are repopulating because if the user to edit changes, we need to hide the user's secondary group.  FIXME we should repopulate the groups privileges list when the primary group is changed in the other tab -- that is, on the change slot of the primary group drop down.
        self._repopulateGroupsPrivileges(excludegroups=[self.userobj.getPrimaryGroup()])
        for group,checkbox in self.secondarygroupcheckboxes.items():
            if group in self.selectedgroups: checkbox.setState(QCheckListItem.On)
            else: checkbox.setState(QCheckListItem.Off)
        
        self.originalgroups = self.selectedgroups[:]
        self.selectedgroups.sort()
        self.__syncGUI()
        self.uidedit.setReadOnly(True)
        self.updatingGUI = False
        self.homedirectoryislinked = False
        if self.exec_()==QDialog.Accepted:
            self.__updateObjectFromGUI(self.userobj)
            # Set the password.
            if self.passwordedit.password()!="":
                self.userobj.setPassword(self.passwordedit.password())
            # Update the groups for this user object. Rudd-O here's when you go in, stud.
        # we collect the selected groups
        self.selectedgroups = [ group for group,checkbox in self.secondarygroupcheckboxes.items() if checkbox.isOn() ]

        for g in self.userobj.getGroups(): # this seems wasteful to remove the user from all groups then re-add, why not a cross check?
            self.userobj.removeFromGroup(g)
        for gn in self.selectedgroups:
            self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

        primarygroupname = unicode(self.primarygroupedit.currentText())
        self.userobj.setPrimaryGroup(self.admincontext.lookupGroupname(primarygroupname))

        # Enable/Disable the account            
        self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.selected())!=0)
        self.admincontext.save()

    ########################################################################
    def showNewUser(self):
        self.updatingGUI = True
        self.newusermode = True
        self.userobj = self.admincontext.newUser(True)

        self.newgroup = self.admincontext.newGroup(True)
        self.newgroup.setGroupname(self.__fudgeNewGroupName(self.userobj.getUsername()))
        self.userobj.setPrimaryGroup(self.newgroup)

        self.selectedgroups = [ u'dialout',u'cdrom',u'floppy',u'audio',u'video',
                                u'plugdev',u'lpadmin',u'scanner']
        homedir = self.__fudgeNewHomeDirectory(self.userobj.getUsername())
        
        # Rudd-O FIXME: now here we tick the proper groups that should be allowed.  Now it selects what userconfig selected before.  FIXME consider adding a drop down that will select the appropriate profile Limited User, Advanced User or Administrator (and see if there is a config file where these profiles can be read).    We are repopulating because if the user to edit changes, we need to hide the user's secondary group.  FIXME we should repopulate the groups privileges list when the primary group is changed in the other tab -- that is, on the change slot of the primary group drop down.
        self._repopulateGroupsPrivileges()
        for group,checkbox in self.secondarygroupcheckboxes.items():
            if group in self.selectedgroups: checkbox.setState(QCheckListItem.On)
            else: checkbox.setState(QCheckListItem.Off)
        
        self.userobj.setHomeDirectory(homedir)
        self.homediredit.setText(homedir)

        shells = self.admincontext.getUserShells()
        dshell = self.admincontext.dshell
        if dshell and (dshell in shells):
            self.userobj.setLoginShell(dshell)
        elif '/bin/bash' in shells:
            self.userobj.setLoginShell('/bin/bash')
        elif '/bin/sh' in shells:
            self.userobj.setLoginShell('/bin/sh')        
        elif len(shells)!=0:
            self.userobj.setLoginShell(shells[0])            

        self.__syncGUI()

        self.uidedit.setReadOnly(False)
        self.updatingGUI = False
        self.homedirectoryislinked = True
        self.passwordedit.erase()
        if self.exec_()==QDialog.Accepted:
            self.__updateObjectFromGUI(self.userobj)

            makehomedir = True
            deleteoldhomedir = False

            if os.path.exists(self.userobj.getHomeDirectory()):
                rc = self.createhomedirectorydialog.do(self.userobj)
                if rc==OverwriteHomeDirectoryDialog.CANCEL:
                    return None
                if rc==OverwriteHomeDirectoryDialog.OK_KEEP:
                    makehomedir = False
                else:
                    deleteoldhomedir = True

            self.admincontext.addUser(self.userobj)

            if self.admincontext.lookupGroupname(self.primarygroupname) is None:
                # Create a new group
                newgroup = self.admincontext.newGroup(True)
                newgroup.setGroupname(self.primarygroupname)
                self.admincontext.addGroup(newgroup)
                self.userobj.setPrimaryGroup(newgroup)

            # Update the groups for this user object. Rudd-O here's when you go in, stud.
	    # we collect the selected groups
	    self.selectedgroups = [ group for group,checkbox in self.secondarygroupcheckboxes.items() if checkbox.isOn() ]
            for gn in self.selectedgroups:
                self.userobj.addToGroup(self.admincontext.lookupGroupname(gn))

            # Set the password.
            if self.passwordedit.password()!="":
                self.userobj.setPassword(self.passwordedit.password())

            # Enable/Disable the account            
            self.userobj.setLocked(self.enabledradiogroup.id(self.enabledradiogroup.selected())!=0)
            self.admincontext.save()

            if deleteoldhomedir:
                if os.path.exists(self.userobj.getHomeDirectory()):
                    shutil.rmtree(self.userobj.getHomeDirectory())
            if makehomedir:
                self.admincontext.createHomeDirectory(self.userobj)

            return self.userobj.getUID()
        else:
            return None

    ########################################################################
    def slotOk(self):
        ok = True
        # Sanity check all values.
        if self.newusermode:
            newusername = unicode(self.realnameedit.text())
            if self.admincontext.lookupUsername(newusername)!=None:
                KMessageBox.sorry(self,i18n("Sorry, you must choose a different user name.\n'%1' is already being used.").arg(newusername))
                ok = False
            else:
                newuid = int(unicode(self.uidedit.text()))
                originaluid = self.userobj.getUID()
                if self.admincontext.lookupUID(newuid)!=None:
                    rc = KMessageBox.questionYesNo(self,i18n("User ID in use"),
                        i18n("Sorry, the UID %1 is already in use. Should %2 be used instead?").arg(newuid).arg(originaluid))
                    if rc==KMessageBox.Yes:
                        self.uidedit.setValue(unicode(originaluid))
                    else:
                        ok = False
                else:
                    self.userobj.setUID(newuid)
        if ok:
            self.passwordedit.clear()
            KDialogBase.slotOk(self)

    ########################################################################
    def slotLoginChanged(self,text):
        newtext = unicode(text)
        if not self.updatingGUI:
            if self.newusermode:
                self.newprimarygroupname = self.__fudgeNewGroupName(newtext)
                self.updatingGUI = True
                self.primarygroupedit.changeItem(self.newprimarygroupname,0)
                if self.homedirectoryislinked:
                    homedir = self.__fudgeNewHomeDirectory(newtext)
                    self.homediredit.setText(homedir)
                self.updatingGUI = False

    ########################################################################
    def slotHomeDirChanged(self,text):
        if self.updatingGUI==False:
            self.homedirectoryislinked = False

    ########################################################################
    def __syncGUI(self):
        if self.userobj.isLocked():
            self.enabledradiogroup.setButton(1)
        else:
            self.enabledradiogroup.setButton(0)

        self.loginnameedit.setText(self.userobj.getUsername())
        self.realnameedit.setText(self.userobj.getRealName())
        self.uidedit.setText(unicode(self.userobj.getUID()))
        self.homediredit.setText(self.userobj.getHomeDirectory())
        self.shelledit.setCurrentText(self.userobj.getLoginShell())

        # Primary Group
        self.primarygroupedit.clear()
        allgroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        allgroups.sort()
        self.availablegroups = allgroups[:]

        try:
            self.availablegroups.remove(self.userobj.getPrimaryGroup().getGroupname())
        except ValueError:
            pass

        if self.newusermode:
            # New user mode
            self.newprimarygroupname = self.__fudgeNewGroupName(unicode(self.userobj.getUsername()))
            primarygroupname = self.newprimarygroupname
            self.primarygroupedit.insertItem(self.newprimarygroupname)
        else:
            # Existing user mode
            primarygroupname = self.userobj.getPrimaryGroup().getGroupname()
        for group in allgroups:
            self.primarygroupedit.insertItem(group)
        self.primarygroupedit.setCurrentText(primarygroupname)

        # If ShadowExpire is turn off then we change the radio box.
        if self.userobj.getExpirationDate() is None:
            self.validradiogroup.setButton(0)
            self.expiredate.setDisabled(True)
            self.expiredate.setDate(SptimeToQDate(99999L))
        else:
            self.validradiogroup.setButton(1)
            self.expiredate.setDisabled(False)
            self.expiredate.setDate(SptimeToQDate(self.userobj.getExpirationDate()))

        if self.userobj.getMaximumPasswordAge() is None:
            # Password aging is turn off
            self.forcepasswordchangecheckbox.setChecked(False)
            d = True
        else:
            # Password aging is turn on
            self.forcepasswordchangecheckbox.setChecked(True)
            d = False
        self.warningedit.setDisabled(d)
        self.maximumpasswordedit.setDisabled(d)
        self.disableexpireedit.setDisabled(d)

        if self.userobj.getPasswordExpireWarning() is None:
            self.warningedit.setValue(0)
        else:
            self.warningedit.setValue(self.userobj.getPasswordExpireWarning())

        if self.userobj.getMaximumPasswordAge() is None:
            self.maximumpasswordedit.setValue(30)
        else:
            self.maximumpasswordedit.setValue(self.userobj.getMaximumPasswordAge())

        if self.userobj.getPasswordDisableAfterExpire() is None:
            self.disableexpireedit.setValue(0)
        else:
            self.disableexpireedit.setValue(self.userobj.getPasswordDisableAfterExpire())

        minage = self.userobj.getMinimumPasswordAgeBeforeChange()
        self.enforcepasswordminagecheckbox.setChecked(minage>0)
        self.minimumpasswordedit.setDisabled(minage<=0)
        if minage<=0:
            minage = 1
        self.minimumpasswordedit.setValue(minage)

        if self.userobj.getLastPasswordChange() in (None,0):
            self.lastchangelabel.setText('-');
        else:
            self.lastchangelabel.setText(KGlobal.locale().formatDate(SptimeToQDate(int(self.userobj.getLastPasswordChange()))))

    ########################################################################
    def __updateObjectFromGUI(self,userobj):
        username = unicode(self.loginnameedit.text())
        userobj.setUsername(username)
        userobj.setRealName(unicode(self.realnameedit.text()))

        userobj.setHomeDirectory(unicode(self.homediredit.text()))
        userobj.setLoginShell(unicode(self.shelledit.currentText()))
        self.primarygroupname = unicode(self.primarygroupedit.currentText())
        groupobj =  self.admincontext.lookupGroupname(self.primarygroupname)
        if groupobj is not None:
            userobj.setPrimaryGroup(groupobj)

        # Password expiration.
        if self.validradiogroup.id(self.validradiogroup.selected())==0:
            # Password is always valid.
            userobj.setExpirationDate(None)
        else:
            # Password will expire at...
            userobj.setExpirationDate(QDateToSptime(self.expiredate.date()))

        if self.forcepasswordchangecheckbox.isChecked():
            userobj.setMaximumPasswordAge(self.maximumpasswordedit.value())
        else:
            userobj.setMaximumPasswordAge(None)

        if self.disableexpireedit.value()==0:
            userobj.setPasswordDisableAfterExpire(None)
        else:
            userobj.setPasswordDisableAfterExpire(self.disableexpireedit.value())

        if self.enforcepasswordminagecheckbox.isChecked():
            userobj.setMinimumPasswordAgeBeforeChange(self.minimumpasswordedit.value())
        else:
            userobj.setMinimumPasswordAgeBeforeChange(0)

        userobj.setPasswordExpireWarning(self.warningedit.value())

    ########################################################################
    def slotBrowseHomeDirClicked(self):
        fileurl = KURL()
        fileurl.setPath(self.homediredit.text())
        self.homedirdialog.setCurrentURL(fileurl)
        if self.homedirdialog.exec_()==QDialog.Accepted:
            self.homediredit.setText(self.homedirdialog.url().path())
            self.homedirectoryislinked = False

    ########################################################################
    def slotValidUntilClicked(self,id):
        if id==0:
            self.expiredate.setDisabled(True)
        else:
            self.expiredate.setDisabled(False)

    ########################################################################
    def slotForcePasswordChangeToggled(self,on):
        on = not on
        self.warningedit.setDisabled(on)
        self.maximumpasswordedit.setDisabled(on)
        self.disableexpireedit.setDisabled(on)

    ########################################################################
    def slotEnforePasswordAgeToggled(self,on):
        self.minimumpasswordedit.setDisabled(not on)

    #######################################################################
    def __fudgeNewGroupName(self,basename):
        if self.admincontext.lookupGroupname(basename) is None:
            return basename
        x = 1
        while self.admincontext.lookupGroupname(basename + u'_' + unicode(x)) is not None:
            x += 1
        return basename + u'_' + unicode(x)

    #######################################################################
    def __fudgeNewHomeDirectory(self,origbasename):
        basename = origbasename.replace("/","")
        if basename=="":
            basename = u"user"

        dhome = self.admincontext.dhome
        if not os.path.isdir(dhome):
            raise OSError, dhome+" does not exist, is it correctly set in "+ \
                    self.admincontext.adduserconf+" ?"
        else:
            # Make sure there's a trailing /
            if dhome[-1] is not '/':
                dhome = dhome+'/'

        if os.path.exists(dhome+basename)==False:
            return dhome+basename
        else:
            x = 1
            while os.path.exists(dhome+basename + u'_' + unicode(x)):
                x += 1
            return dhome+basename


###########################################################################
class LoginNameValidator(QValidator):
    def __init__(self,parent):
        QValidator.__init__(self,parent)

    #######################################################################
    def validate(self,inputstr,pos):
        instr = unicode(inputstr)
        if len(instr)==0:
            return (QValidator.Intermediate,pos)
        for c in instr:
            if ord(c)<0x20 or ord(c)>0x7f or c.isspace() or c==":" or c=="," or c==".":
                return (QValidator.Invalid,pos)

        # Try to encode this string in the system encoding.
        try:
            instr.encode(locale.getpreferredencoding())
        except UnicodeEncodeError:
            # won't encode -> reject it.
            return (QValidator.Invalid,pos)

        return (QValidator.Acceptable,pos)

    #######################################################################
    def fixup(self,inputstr):
        instr = unicode(inputstr)
        newstr = ""
        for c in instr:
            if (ord(c)<0x20 or ord(c)>0x7f or c.isspace() or c==":" or c=="," or c==".")==False:
                newstr += c

        if newstr=="":
            return "user"
        else:
            return newstr

###########################################################################
class RealUserNameValidator(QValidator):
    def __init__(self,parent):
        QValidator.__init__(self,parent)

    #######################################################################
    def validate(self,inputstr,pos):
        instr = unicode(inputstr)
        for c in instr:
            if c==":":
                return (QValidator.Invalid,pos)

        # Try to encode this string in the system encoding.
        try:
            instr.encode(locale.getpreferredencoding())
        except UnicodeEncodeError:
            # won't encode -> reject it.
            return (QValidator.Invalid,pos)

        return (QValidator.Acceptable,pos)

    #######################################################################
    def fixup(self,inputstr):
        return unicode(inputstr).replace(":","")

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
class UserDeleteDialog(KDialog):
    def __init__(self,parent,admincontext):
        KDialog.__init__(self,parent)
        self.setModal(True)#,Qt.WType_Dialog)
        self.setCaption(i18n("Delete User Account"))
        self.admincontext = admincontext
        self.updatingGUI = True

        toplayout = QVBoxLayout(self)
        toplayout.setSpacing(self.spacingHint())
        toplayout.setMargin(self.marginHint())

        contentbox = KHBox(self)
        contentbox.setSpacing(self.spacingHint())
        toplayout.addWidget(contentbox)
        toplayout.setStretchFactor(contentbox,1)

        label = QLabel(contentbox)
        #label.setPixmap(KGlobal.iconLoader().loadIcon("messagebox_warning", KIcon.NoGroup, KIcon.SizeMedium,
            #KIcon.DefaultState, None, True)) # TODO
        contentbox.setStretchFactor(label,0)

        textbox = KVBox(contentbox)

        textbox.setSpacing(self.spacingHint())
        textbox.setMargin(self.marginHint())

        self.usernamelabel = QLabel("",textbox)
        textbox.setStretchFactor(self.usernamelabel,0)

        # Remove directory checkbox.
        self.deletedirectorycheckbox = QCheckBox(i18n("Delete home directory ()"),textbox)
        textbox.setStretchFactor(self.deletedirectorycheckbox,0)

        # Delete the User's private group.
        self.deletegroupcheckbox = QCheckBox(i18n("Delete group ()"),textbox)
        textbox.setStretchFactor(self.deletegroupcheckbox ,0)

        # Buttons
        buttonbox = KHBox(self)
        toplayout.addWidget(buttonbox)

        buttonbox.setSpacing(self.spacingHint())
        toplayout.setStretchFactor(buttonbox,0)

        spacer = QWidget(buttonbox)
        buttonbox.setStretchFactor(spacer,1)

        okbutton = QPushButton(i18n("OK"),buttonbox)
        buttonbox.setStretchFactor(okbutton,0)
        self.connect(okbutton,SIGNAL("clicked()"),self.slotOkClicked)

        cancelbutton = QPushButton(i18n("Cancel"),buttonbox)
        cancelbutton.setDefault(True)
        buttonbox.setStretchFactor(cancelbutton,0)
        self.connect(cancelbutton,SIGNAL("clicked()"),self.slotCancelClicked)

    def deleteUser(self,userid):
        # Setup the 
        userobj = self.admincontext.lookupUID(userid)
        self.usernamelabel.setText(i18n("Are you sure want to delete user account '%1' (%2)?").arg(userobj.getUsername()).arg(userobj.getUID()) )
        self.deletedirectorycheckbox.setChecked(False)
        self.deletedirectorycheckbox.setText(i18n("Delete home directory (%1)").arg(userobj.getHomeDirectory()))
        primarygroupobj = userobj.getPrimaryGroup()
        primarygroupname = primarygroupobj.getGroupname()
        self.deletegroupcheckbox.setText(i18n("Delete group '%1' (%2)").arg(primarygroupname).arg(primarygroupobj.getGID()))
        self.deletegroupcheckbox.setChecked(len(primarygroupobj.getUsers())==1)
        if self.exec_()==QDialog.Accepted:
            self.admincontext.removeUser(userobj)
            if self.deletedirectorycheckbox.isChecked():
                self.admincontext.removeHomeDirectory(userobj)
                # FIXME
                #self.admincontext.removeMail(userobj)
            if self.deletegroupcheckbox.isChecked():
                self.admincontext.removeGroup(primarygroupobj)
            self.admincontext.save()
            return True
        else:
            return False

    def slotOkClicked(self):
        self.accept()

    def slotCancelClicked(self):
        self.reject()

###########################################################################
class OverwriteHomeDirectoryDialog(KDialog):
    CANCEL = 0
    OK_KEEP = 1
    OK_REPLACE = 2

    def __init__(self,parent):
        KDialog.__init__(self,parent)
        self.setModal(True)
        #,Qt.WType_Dialog)
        self.setCaption(i18n("Create home directory"))
        self.updatingGUI = True

        toplayout = QVBoxLayout(self)
        toplayout.setSpacing(self.spacingHint())
        toplayout.setMargin(self.marginHint())

        contentbox = KHBox(self)
        contentbox.setSpacing(self.spacingHint())
        toplayout.addWidget(contentbox)
        toplayout.setStretchFactor(contentbox,1)

        label = QLabel(contentbox)
        #label.setPixmap(KGlobal.iconLoader().loadIcon("messagebox_warning", KIcon.NoGroup, KIcon.SizeMedium,
            #KIcon.DefaultState, None, True))   # TODO
        contentbox.setStretchFactor(label,0)

        textbox = KVBox(contentbox)

        textbox.setSpacing(self.spacingHint())
        textbox.setMargin(self.marginHint())

        # "%dir was selected as the home directory for %user. This directory already exists. Shall I:."
        self.toplabel = QLabel("",textbox)
        textbox.setStretchFactor(self.toplabel,0)

        self.radiogroup = QButtonGroup()
        #self.radiogroup.setRadioButtonExclusive(True)  # TODO

        # Use Existing home directory radio button.
        self.usehomedirectoryradio = QRadioButton(i18n("Use the existing directory without changing it."),textbox)
        textbox.setStretchFactor(self.usehomedirectoryradio,0)

        # Replace home directory radio button
        self.replacehomedirectoryradio = QRadioButton(i18n("Delete the directory and replace it with a new home directory."),textbox)
        textbox.setStretchFactor(self.replacehomedirectoryradio ,0)

        self.radiogroup.addButton(self.usehomedirectoryradio,0)
        self.radiogroup.addButton(self.replacehomedirectoryradio,1)

        # Buttons
        buttonbox = KHBox(self)
        toplayout.addWidget(buttonbox)

        buttonbox.setSpacing(self.spacingHint())
        toplayout.setStretchFactor(buttonbox,0)

        spacer = QWidget(buttonbox)
        buttonbox.setStretchFactor(spacer,1)

        okbutton = QPushButton(i18n("OK"),buttonbox)
        buttonbox.setStretchFactor(okbutton,0)
        self.connect(okbutton,SIGNAL("clicked()"),self.slotOkClicked)

        cancelbutton = QPushButton(i18n("Cancel"),buttonbox)
        cancelbutton.setDefault(True)
        buttonbox.setStretchFactor(cancelbutton,0)
        self.connect(cancelbutton,SIGNAL("clicked()"),self.slotCancelClicked)

    def do(self,userobj):
        # Setup the 
        self.toplabel.setText(i18n("The directory '%1' was entered as the home directory for new user '%2'.\n This directory already exists.") \
            .arg(userobj.getHomeDirectory()).arg(userobj.getUsername()) )
        self.radiogroup.setButton(0)

        if self.exec_()==QDialog.Accepted:
            if self.radiogroup.selectedId()==0:
                return OverwriteHomeDirectoryDialog.OK_KEEP
            else:
                return OverwriteHomeDirectoryDialog.OK_REPLACE
        else:
            return OverwriteHomeDirectoryDialog.CANCEL

    def slotOkClicked(self):
        self.accept()

    def slotCancelClicked(self):
        self.reject()

###########################################################################
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
        item = self.availablelist.selectedItem()
        if item!=None:
            self.selectedlist.insertItem(item.text())
            self.availablelist.removeItem(self.availablelist.index(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    #######################################################################
    def slotRemoveClicked(self):
        item = self.selectedlist.selectedItem()
        if item!=None:
            self.availablelist.insertItem(item.text())
            self.selectedlist.removeItem(self.selectedlist.index(item))
            self._selectFirstAvailable()
            self._selectFirstSelected()
            self.addbutton.setDisabled(self.availablelist.selectedItem()==None)
            self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    #######################################################################
    def __updateLists(self,grouplist,selectedlist):
        self.selectedlist.clear()
        for item in selectedlist:
            self.selectedlist.insertItem(item)
        self.selectedlist.sort()

        self.availablelist.clear()
        for item in grouplist:
            if item not in selectedlist:
                self.availablelist.insertItem(item)
        self.availablelist.sort()

        self._selectFirstAvailable()
        self.addbutton.setDisabled(self.availablelist.selectedItem()==None)

        self._selectFirstSelected()
        self.removebutton.setDisabled(self.selectedlist.selectedItem()==None)

    #######################################################################
    def _selectFirstAvailable(self):
        if self.availablelist.count()!=0:
            if self.availablelist.selectedItem()==None:
                self.availablelist.setSelected(0,True)

    #######################################################################
    def _selectFirstSelected(self):
        if self.selectedlist.count()!=0:
            if self.selectedlist.selectedItem()==None:
                self.selectedlist.setSelected(0,True)

    #######################################################################
    def __fudgeNewGroupName(self,basename):
        availablegroups = [g.getGroupname() for g in self.admincontext.getGroups()]
        if basename not in availablegroups:
            return basename
        x = 1
        while basename + u'_' + unicode(x) in availablegroups:
            x += 1
        return basename + u'_' + unicode(x)

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
