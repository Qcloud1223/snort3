//--------------------------------------------------------------------------
// Copyright (C) 2016-2019 Cisco and/or its affiliates. All rights reserved.
//
// This program is free software; you can redistribute it and/or modify it
// under the terms of the GNU General Public License Version 2 as published
// by the Free Software Foundation.  You may not use, modify or distribute
// this program under any other version of the GNU General Public License.
//
// This program is distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
// General Public License for more details.
//
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
//--------------------------------------------------------------------------

// appid_inspector.h author davis mcpherson <davmcphe@cisco.com>
// Created on: May 10, 2016

#ifndef APPID_INSPECTOR_H
#define APPID_INSPECTOR_H

#include "appid_config.h"
#include "appid_module.h"
#include "application_ids.h"
#include "flow/flow.h"

namespace snort
{
struct Packet;
struct SnortConfig;
}
class SipEventHandler;

class AppIdInspector : public snort::Inspector
{
public:

    AppIdInspector(AppIdModule&);
    ~AppIdInspector() override;

    bool configure(snort::SnortConfig*) override;
    void show(snort::SnortConfig*) override;
    void tinit() override;
    void tterm() override;
    void eval(snort::Packet*) override;
    AppIdContext* get_ctxt();

    SipEventHandler& get_sip_event_handler()
    {
        return *my_seh;
    }

private:
    const AppIdConfig* config = nullptr;
    AppIdContext* ctxt = nullptr;
    SipEventHandler* my_seh = nullptr;

};

extern THREAD_LOCAL ThirdPartyAppIdContext* tp_appid_thread_ctxt;

#endif

