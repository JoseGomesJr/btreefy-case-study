/**
 * Zbus channels shared by both tracker policies (BT and FSM).
 *
 * The policy under test — whichever one is linked in via
 * CONFIG_TRACKER_POLICY_BT / CONFIG_TRACKER_POLICY_FSM — never talks to a
 * driver directly. It only observes these channels (through the blackboard,
 * see tracker_bb.h) and publishes to chan_tracker_cmd. This is what makes
 * the BT-vs-FSM comparison a structural property instead of a promise: see
 * CLAUDE.md rule 4 in btreefy-tracking/.
 */

#ifndef TRACKER_EVENTS_H
#define TRACKER_EVENTS_H

#include <stdbool.h>
#include <stdint.h>

#include <zephyr/zbus/zbus.h>

enum gnss_evt_status
{
    GNSS_BUSY,
    GNSS_FIX,
    GNSS_FAIL,
};

struct gnss_fix
{
    int32_t lat_e7;
    int32_t lon_e7;
};

struct gnss_evt
{
    enum gnss_evt_status st;
    struct gnss_fix       fix;
};

enum radio_evt_status
{
    RADIO_BUSY,
    RADIO_OK,
    RADIO_FAIL,
};

struct radio_evt
{
    enum radio_evt_status st;
};

struct sensor_evt
{
    bool    tamper;
    uint8_t battery_pct;
};

// Level-based, like sensor_evt.tamper: test/oracle code (fake_request_new_position)
// drives it, the policy only observes it through the blackboard.
struct request_evt
{
    bool new_position_requested;
};

enum tracker_cmd_op
{
    CMD_SLEEP,
    CMD_FIX_START,
    CMD_FIX_STOP,
    CMD_SEND_POS,
    CMD_SEND_ALERT,
    CMD_LOG_FAIL,
};

struct tracker_cmd
{
    enum tracker_cmd_op op;
};

ZBUS_CHAN_DECLARE(chan_gnss_evt, chan_radio_evt, chan_sensor_evt, chan_request_evt,
                   chan_tracker_cmd);

ZBUS_OBS_DECLARE(sub_policy);

#endif  // TRACKER_EVENTS_H
