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
#ifndef HELPER_H
#define HELPER_H

#include <KAuth/ActionReply>

using namespace KAuth;

class Helper: public QObject
{
    Q_OBJECT
public Q_SLOTS:
    ActionReply load(QVariantMap args);
    ActionReply save(QVariantMap args);
    ActionReply createhomedirectory(QVariantMap args);
    ActionReply removehomedirectory(QVariantMap args);
};

#endif /* HELPER_H */
