/**
 * Static blackboard shared by both policies. Updated by tracker_bb_update()
 * from whichever zbus channel just fired; read by the BT leaves / FSM state
 * run-functions — never touched directly by a driver.
 */

#ifndef TRACKER_BB_H
#define TRACKER_BB_H

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/zbus/zbus.h>

#include "tracker/tracker_events.h"

struct tracker_bb
{
    enum gnss_evt_status  gnss_status;
    struct gnss_fix       last_fix;
    enum radio_evt_status radio_status;
    bool                  tamper;
    uint8_t               battery_pct;
    bool                  new_position_requested;
};

// Single static instance — no malloc, matches BTreeFy's own static
// allocation rule (CLAUDE.md rule 2).
extern struct tracker_bb g_tracker_bb;

// Copies the payload of a just-fired channel into g_tracker_bb. Safe to
// call for any channel the policy subscriber observes; no-op for others.
void tracker_bb_update(const struct zbus_channel *chan);

#endif  // TRACKER_BB_H
