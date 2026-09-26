/* SPDX-License-Identifier: MIT */
#include "latency_trace.h"

#include <string.h>

static uint32_t stage_bit(lt_stage_t stage) {
    return 1u << (uint32_t)stage;
}

static bool valid_stage(lt_stage_t stage) {
    return stage >= LT_STAGE_DRDY && stage < LT_STAGE_COUNT;
}

static uint32_t required_predecessors(lt_stage_t stage) {
    switch (stage) {
    case LT_STAGE_DRDY:
        return 0u;
    case LT_STAGE_SPI_DMA_DONE:
        return stage_bit(LT_STAGE_DRDY);
    case LT_STAGE_PROCESS_DONE:
        return stage_bit(LT_STAGE_SPI_DMA_DONE);
    case LT_STAGE_LOCAL_EVENT:
        return stage_bit(LT_STAGE_PROCESS_DONE);
    case LT_STAGE_OBSERVER_TX:
        /* Observer delivery is never part of the local critical path. */
        return stage_bit(LT_STAGE_PROCESS_DONE);
    case LT_STAGE_COUNT:
    default:
        return UINT32_MAX;
    }
}

void lt_trace_init(lt_trace_t *trace, uint32_t sequence, const char *clock_domain) {
    size_t i;

    if (trace == NULL) {
        return;
    }
    memset(trace, 0, sizeof(*trace));
    trace->sequence = sequence;
    if (clock_domain == NULL) {
        return;
    }

    for (i = 0; i + 1u < LT_CLOCK_DOMAIN_NAME_MAX && clock_domain[i] != '\0'; ++i) {
        trace->clock_domain[i] = clock_domain[i];
    }
    trace->clock_domain[i] = '\0';
}

bool lt_trace_has_stage(const lt_trace_t *trace, lt_stage_t stage) {
    if (trace == NULL || !valid_stage(stage)) {
        return false;
    }
    return (trace->present_mask & stage_bit(stage)) != 0u;
}

lt_result_t lt_trace_mark(lt_trace_t *trace, lt_stage_t stage, uint64_t timestamp_ns) {
    uint32_t bit;
    uint32_t required;
    uint32_t i;

    if (trace == NULL || !valid_stage(stage)) {
        return LT_ERR_ARGUMENT;
    }
    bit = stage_bit(stage);
    if ((trace->present_mask & bit) != 0u) {
        return LT_ERR_DUPLICATE_STAGE;
    }

    required = required_predecessors(stage);
    if ((trace->present_mask & required) != required) {
        return LT_ERR_STAGE_ORDER;
    }

    /* No marked stage may be later than a new timestamp. */
    for (i = 0u; i < (uint32_t)LT_STAGE_COUNT; ++i) {
        if ((trace->present_mask & (1u << i)) != 0u && timestamp_ns < trace->timestamp_ns[i]) {
            return LT_ERR_TIME_ORDER;
        }
    }

    trace->timestamp_ns[stage] = timestamp_ns;
    trace->present_mask |= bit;
    return LT_OK;
}

lt_result_t lt_trace_delta_ns(const lt_trace_t *trace,
                              lt_stage_t start,
                              lt_stage_t end,
                              uint64_t *delta_ns) {
    if (trace == NULL || delta_ns == NULL || !valid_stage(start) || !valid_stage(end)) {
        return LT_ERR_ARGUMENT;
    }
    if (!lt_trace_has_stage(trace, start) || !lt_trace_has_stage(trace, end)) {
        return LT_ERR_MISSING_STAGE;
    }
    if (trace->timestamp_ns[end] < trace->timestamp_ns[start]) {
        return LT_ERR_TIME_ORDER;
    }
    *delta_ns = trace->timestamp_ns[end] - trace->timestamp_ns[start];
    return LT_OK;
}

bool lt_clock_is_usable(const lt_clock_health_t *health,
                        uint32_t configured_max_uncertainty_ns) {
    return health != NULL && health->synchronized &&
           health->uncertainty_ns <= configured_max_uncertainty_ns;
}
