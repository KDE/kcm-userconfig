/*
 * A KCModule for user and group configuration
 *
 * Copyright 2011 Romain Perier.
 *
 * Authors:
 * - Romain Perier <romain.perier@gmail.com>
 *
 * License: GPL v3
 */
#include "helper.h"

#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <cerrno>
#include <cstring>
#include <cstdio>

#include <KAuth/HelperSupport>
#include <QDir>
#include <QTemporaryFile>
#include <QTextStream>


// FIXME: factorize these three functions
static void copytree(const QString& src, const QString& dst)
{
    QDir srcDir(src);
    QDir dstDir(dst);

    if(!srcDir.exists())
        return;
    if(!dstDir.exists())
        dstDir.mkdir(dst);

    QStringList files = srcDir.entryList(QDir::Files | QDir::Hidden);
    for(int i = 0; i < files.count(); i++) {
        QString srcName = src + "/" + files[i];
        QString dstName = dst + "/" + files[i];
        QFile::copy(srcName, dstName);
    }
    files.clear();
    files = srcDir.entryList(QDir::AllDirs | QDir::NoDotAndDotDot);
    for(int i = 0; i < files.count(); i++) {
        QString srcName = src + "/" + files[i];
        QString dstName = dst + "/" + files[i];
        copytree(srcName, dstName);
    }
}

static void rmtree(const QString &dir)
{
    QDir currDir(dir);

    if(!currDir.exists())
        return;
    QStringList files = currDir.entryList(QDir::Files | QDir::Hidden);
    for(int i = 0; i < files.count(); i++)
        QFile::remove(dir + "/" + files[i]);
    files.clear();
    files = currDir.entryList(QDir::AllDirs | QDir::NoDotAndDotDot);
    for(int i = 0; i < files.count(); i++)
        rmtree(dir + "/" + files[i]);
    currDir.rmdir(dir);
}

static void lchowntree(const QString &path, uid_t owner, gid_t group)
{
    QDir currDir(path);

    if(!currDir.exists())
        return;
    lchown(qPrintable(path), owner, group);
    QStringList files = currDir.entryList(QDir::Files | QDir::Hidden);
    for(int i = 0; i < files.count(); i++)
        lchown(qPrintable(path + "/" + files[i]), owner, group);
    files.clear();
    files = currDir.entryList(QDir::AllDirs | QDir::NoDotAndDotDot);
    for(int i = 0; i < files.count(); i++)
        lchowntree(path + "/" + files[i], owner, group);
}

static bool applyChanges(const QString& path, const QString &content)
{
    QTemporaryFile tmpFile(path);
    struct flock flock = {
      F_WRLCK,  // l_type
      SEEK_SET, // l_whence
      0,        // l_start
      0,        // l_len
      getpid()  // l_pid
    };

    if (!tmpFile.open())
        return false;
    tmpFile.setAutoRemove(false);
    if (!tmpFile.setPermissions(QFile::ReadOwner|QFile::WriteOwner|QFile::ReadGroup|QFile::ReadOther))
        return false;
    if (tmpFile.write(content.toLocal8Bit()) == -1)
        return false;
    QFile file(path);
    if (!file.open(QIODevice::WriteOnly))
        return false;
    if (fcntl(file.handle(), F_SETLK, &flock) == -1)
        return false;
    rename(qPrintable(tmpFile.fileName()), qPrintable(path));
    return true;
}


ActionReply Helper::load(QVariantMap args)
{
    ActionReply reply;
    QString fileName = args["fileName"].toString();
    QFile file(fileName);

    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        reply = ActionReply::HelperErrorReply;
	reply.addData("output", file.errorString());
	return reply;
    }
    QTextStream stream(&file);
    // If the file is large it will consume a significant amount of memory
    reply.addData("fileContents", stream.readAll());
    return reply;
}

//FIXME: /etc/gshadow must be supported
ActionReply Helper::save(QVariantMap args)
{
    ActionReply reply;
    QString passwdFileContents = args["passwdFileContents"].toString();
    QString groupFileContents = args["groupFileContents"].toString();
    QString shadowFileContents = args["shadowFileContents"].toString();

    if (!applyChanges("/etc/passwd", passwdFileContents))
        goto fail;
    if (!applyChanges("/etc/group", groupFileContents))
        goto fail;
    if (!applyChanges("/etc/shadow", shadowFileContents))
        goto fail;
    goto ok;
fail:
    reply = ActionReply::HelperErrorReply;
    reply.addData("output", strerror(errno));
ok:
    return reply;
}

ActionReply Helper::createhomedirectory(QVariantMap args)
{
    ActionReply reply;
    QString skel = args["skel"].toString();
    QString directory = args["directory"].toString();
    mode_t mode = args["dir_mode"].toUInt();
    uid_t owner = args["uid"].toUInt();
    gid_t group = args["gid"].toUInt();

    copytree(skel, directory);
    if (chmod(qPrintable(directory), mode) == -1) {
        reply = ActionReply::HelperErrorReply;
	reply.addData("output", strerror(errno));
	return reply;
    }
    lchowntree(directory, owner, group);
    return reply;
}

ActionReply Helper::removehomedirectory(QVariantMap args)
{
    QString directory = args["directory"].toString();
    rmtree(directory);
    return ActionReply();
}

KDE4_AUTH_HELPER_MAIN("org.kde.kcontrol.userconfig", Helper)
