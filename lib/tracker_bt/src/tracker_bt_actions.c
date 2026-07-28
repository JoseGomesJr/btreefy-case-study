
#include <zephyr/zbus/zbus.h>

#include "btreefy/btreefy_objs.h"
#include "tracker/tracker_bb.h"
#include "tracker/tracker_events.h"

#ifdef CONFIG_TRACKER_WITH_TAMPER

enum btf_node_status cond_tamper_detected(struct btf_tree *tree)
{
    ARG_UNUSED(tree);
    return g_tracker_bb.tamper ? BTF_SUCCESS_STATUS : BTF_FAILURE_STATUS;
}

enum btf_node_status action_send_tamper_alert(struct btf_tree *tree)
{
    ARG_UNUSED(tree);
    struct tracker_cmd cmd = {.op = CMD_SEND_ALERT};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
    return BTF_SUCCESS_STATUS;
}

#endif  // CONFIG_TRACKER_WITH_TAMPER

enum btf_node_status cond_new_position_requested(struct btf_tree *tree)
{
    ARG_UNUSED(tree);
    return g_tracker_bb.new_position_requested ? BTF_SUCCESS_STATUS : BTF_FAILURE_STATUS;
}

enum btf_node_status action_gnss_fix(struct btf_tree *tree)
{
    ARG_UNUSED(tree);

    switch (g_tracker_bb.gnss_status)
    {
        case GNSS_FIX:
            return BTF_SUCCESS_STATUS;
        case GNSS_FAIL:
            return BTF_FAILURE_STATUS;
        case GNSS_BUSY:
        default:
        {
            struct tracker_cmd cmd = {.op = CMD_FIX_START};
            zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
            return BTF_RUNNING_STATUS;
        }
    }
}

enum btf_node_status action_send_position(struct btf_tree *tree)
{
    ARG_UNUSED(tree);

    switch (g_tracker_bb.radio_status)
    {
        case RADIO_OK:
            return BTF_SUCCESS_STATUS;
        case RADIO_FAIL:
            return BTF_FAILURE_STATUS;
        case RADIO_BUSY:
        default:
        {
            struct tracker_cmd cmd = {.op = CMD_SEND_POS};
            zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
            return BTF_RUNNING_STATUS;
        }
    }
}

enum btf_node_status action_register_positioning_failure(struct btf_tree *tree)
{
    ARG_UNUSED(tree);
    struct tracker_cmd cmd = {.op = CMD_LOG_FAIL};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
    return BTF_SUCCESS_STATUS;
}

enum btf_node_status action_sleep(struct btf_tree *tree)
{
    ARG_UNUSED(tree);
    struct tracker_cmd cmd = {.op = CMD_SLEEP};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
    return BTF_SUCCESS_STATUS;
}
