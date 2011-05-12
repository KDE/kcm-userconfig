/*
 * Copyright 2011  Romain Perier <romain.perier@gmail.com>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of 
 * the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
