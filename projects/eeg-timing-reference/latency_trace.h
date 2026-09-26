/*
 * latency_trace.h -- bounded, allocation-free timing instrumentation for a
 * non-clinical acquisition-edge prototype.
 *
 * This file deliberately has no electrode, analogue-front-end, feedback,
 * diagnostic, or network-driver logic. It records timestamps supplied by a
 * board-specific clock layer so that an integration team can measure its
 * latency budget rather than assume that a network or a processor is "real
 * time".
 *
 * SPDX-License-Identifier: MIT
 */
#ifndef EEG_TIMING_REFERENCE_LATENCY_TRACE_H
#define EEG_TIMING_REFERENCE_LATENCY_TRACE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define LT_CLOCK_DOMAIN_NAME_MAX 16u

/*
 * Stage order is intentional.  The local acquisition edge stamps DRDY before
 * DMA work begins.  An observer/network timestamp is after local processing
 * and is never a prerequisite for a local decision.
 */
typedef enum {
    LT_STAGE_DRDY = 0,          /* AFE data-ready edge captured */
    LT_STAGE_SPI_DMA_DONE,      /* complete sample frame in RAM */
    LT_STAGE_PROCESS_DONE,      /* local, versioned processing completed */
    LT_STAGE_LOCAL_EVENT,       /* local visual/auditory event requested */
    LT_STAGE_OBSERVER_TX,       /* optional read-only observer frame queued */
    LT_STAGE_COUNT
} lt_stage_t;

typedef enum {
    LT_OK = 0,
    LT_ERR_ARGUMENT,
    LT_ERR_DUPLICATE_STAGE,
    LT_ERR_STAGE_ORDER,
    LT_ERR_TIME_ORDER,
    LT_ERR_MISSING_STAGE
} lt_result_t;

/*
 * clock_domain names the disciplined clock time base, e.g. "PTP-1". It is
 * metadata for a trace export; callers must copy a bounded ASCII name.
 */
typedef struct {
    uint32_t sequence;
    char clock_domain[LT_CLOCK_DOMAIN_NAME_MAX];
    uint64_t timestamp_ns[LT_STAGE_COUNT];
    uint32_t present_mask;
} lt_trace_t;

/* Clock-health input supplied by a PTP/gPTP service, not inferred here. */
typedef struct {
    bool synchronized;
    uint32_t uncertainty_ns;
} lt_clock_health_t;

void lt_trace_init(lt_trace_t *trace, uint32_t sequence, const char *clock_domain);

/*
 * Adds one point to a trace. Stages cannot be rewritten. Required predecessor
 * points must already exist, and a timestamp must not precede an earlier point.
 */
lt_result_t lt_trace_mark(lt_trace_t *trace, lt_stage_t stage, uint64_t timestamp_ns);

bool lt_trace_has_stage(const lt_trace_t *trace, lt_stage_t stage);

/* Returns end - start only for two present, monotonically ordered points. */
lt_result_t lt_trace_delta_ns(const lt_trace_t *trace,
                              lt_stage_t start,
                              lt_stage_t end,
                              uint64_t *delta_ns);

/*
 * A caller-owned acceptance limit makes the clock health check test-plan
 * driven. This module never invents a "safe" latency or uncertainty limit.
 */
bool lt_clock_is_usable(const lt_clock_health_t *health,
                        uint32_t configured_max_uncertainty_ns);

#ifdef __cplusplus
}
#endif

#endif /* EEG_TIMING_REFERENCE_LATENCY_TRACE_H */
