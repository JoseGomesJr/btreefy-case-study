#include <zephyr/kernel.h>
#include <zephyr/zbus/zbus.h>

#include "tracker/tracker_events.h"

static const char *cmd_op_name(enum tracker_cmd_op op)
{
    switch (op)
    {
        case CMD_SLEEP:
            return "CMD_SLEEP";
        case CMD_FIX_START:
            return "CMD_FIX_START";
        case CMD_FIX_STOP:
            return "CMD_FIX_STOP";
        case CMD_SEND_POS:
            return "CMD_SEND_POS";
        case CMD_SEND_ALERT:
            return "CMD_SEND_ALERT";
        case CMD_LOG_FAIL:
            return "CMD_LOG_FAIL";
        default:
            return "CMD_UNKNOWN";
    }
}

static void trace_cb(const struct zbus_channel *chan)
{
    if (chan == &chan_tracker_cmd)
    {
        const struct tracker_cmd *cmd = zbus_chan_const_msg(chan);
        printk("TR,%u,%s,%s\n", k_cycle_get_32(), zbus_chan_name(chan), cmd_op_name(cmd->op));
    }
    else
    {
        printk("TR,%u,%s\n", k_cycle_get_32(), zbus_chan_name(chan));
    }
}

ZBUS_LISTENER_DEFINE(trace_probe, trace_cb);

static bool attach_trace_probe(const struct zbus_channel *chan, void *user_data)
{
    ARG_UNUSED(user_data);
    (void) zbus_chan_add_obs(chan, &trace_probe, K_MSEC(10));
    return true;
}

static int trace_probe_init(void)
{
    zbus_iterate_over_channels_with_user_data(attach_trace_probe, NULL);
    return 0;
}

SYS_INIT(trace_probe_init, APPLICATION, 90);
