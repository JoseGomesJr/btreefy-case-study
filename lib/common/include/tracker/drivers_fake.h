/**
 * Fake GNSS/radio/tamper-sensor drivers, shared identically by both
 * policies (BT and FSM) — see CLAUDE.md rule 4 in btreefy-tracking/: the
 * policy never touches these directly, only through chan_tracker_cmd and
 * the blackboard. Test/oracle code (Fase 5) drives these functions to
 * script event sequences.
 */

#ifndef TRACKER_DRIVERS_FAKE_H
#define TRACKER_DRIVERS_FAKE_H

#include <stdbool.h>
#include <stdint.h>

#include "tracker/tracker_events.h"

// Test/oracle control surface — publishes the corresponding event.
void fake_gnss_finish(enum gnss_evt_status st, struct gnss_fix fix);
void fake_radio_finish(enum radio_evt_status st);
void fake_sensor_set_tamper(bool tamper);
void fake_sensor_set_battery(uint8_t battery_pct);
void fake_request_new_position(bool active);

#endif  // TRACKER_DRIVERS_FAKE_H
