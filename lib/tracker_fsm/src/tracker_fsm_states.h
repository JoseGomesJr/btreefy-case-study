
#ifndef TRACKER_FSM_STATES_H
#define TRACKER_FSM_STATES_H

#include <zephyr/smf.h>

enum tracker_fsm_state_id
{
    STATE_SLEEP,
    STATE_GNSS_FIX,
    STATE_SEND_POSITION,
    STATE_REGISTER_FAILURE,
#ifdef CONFIG_TRACKER_WITH_TAMPER
    STATE_TAMPER_ALERT,
#endif
};

extern const struct smf_state tracker_fsm_states[];

#endif  // TRACKER_FSM_STATES_H
