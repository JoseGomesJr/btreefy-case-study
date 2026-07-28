/*
 * Copyright (c) 2012-2014 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <stdio.h>

#include <zephyr/kernel.h>

#include "tracker/drivers_fake.h"

int main(void)
{
    printf("BTreeFy tracker eval — tracker_v0 smoke test (whichever policy is linked in)\n");

    fake_sensor_set_battery(80);
    fake_sensor_set_tamper(false);
    k_msleep(50);

    printf("--- new position requested ---\n");
    fake_request_new_position(true);
    k_msleep(50);

    printf("--- GNSS fix succeeds ---\n");
    fake_gnss_finish(GNSS_FIX, (struct gnss_fix){.lat_e7 = -94900000, .lon_e7 = -364700000});
    k_msleep(50);

    printf("--- radio send succeeds ---\n");
    fake_radio_finish(RADIO_OK);
    k_msleep(50);

    printf("--- request cleared (oracle/test owns this, not the policy) ---\n");
    fake_request_new_position(false);
    k_msleep(50);

    printf("--- tamper detected ---\n");
    fake_sensor_set_tamper(true);
    k_msleep(50);

    printf("--- unrelated event while tamper persists ---\n");
    fake_sensor_set_battery(75);
    k_msleep(50);

    printf("--- tamper cleared ---\n");
    fake_sensor_set_tamper(false);
    k_msleep(50);

    return 0;
}
