# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Dict, List, Optional

from npusim.prof.src.backend.hints.base.hint_base import (
    HintDataItem,
    HintTarget,
    IHint,
)
from npusim.prof.src.backend.database import database_handler
from npusim.prof.src.common.biprof_constants import core_num_map
from npusim.prof.src.common.biprof_context import biprof_ctx
from npusim.prof.src.common.biprof_enum import ArchName


class SmallGridHint(IHint):
    # Kernel-level hint: detects that the operator uses only a small
    # fraction of available execution cores (a "small grid"). On V100,
    # each physical CoreId has two independently launched AIV sub-cores.
    # Count (CoreId, CoreTypeId) pairs for vector kernels so that 16
    # physical IDs with AIV0 and AIV1 equal all 32 available AIV lanes.
    # For non-vector kernels, retain the physical-core count.

    @staticmethod
    def get_name() -> str:
        return "small_grid_hint"

    def process(self, instrs_map: Dict[Optional[int], List]) -> List[HintDataItem]:
        arch_raw = biprof_ctx.arch
        if not arch_raw:
            arch_raw = database_handler.get_arch()
        if not arch_raw:
            return self.result
        try:
            arch = ArchName[str(arch_raw).upper()]
        except (KeyError, ValueError):
            return self.result
        max_cores = core_num_map.get(arch)
        if not max_cores:
            return self.result

        rows = database_handler.execute(
            """SELECT DISTINCT ExecInstrCoreId, CoreTypeId
               FROM ExecutedInstructions WHERE CoreTypeId IN (2, 3)"""
        ).fetchall()
        if not rows:
            rows = database_handler.execute(
                "SELECT DISTINCT ExecInstrCoreId FROM ExecutedInstructions"
            ).fetchall()
        active = len(rows)
        if active <= max_cores // 2:
            self.add_hint(
                (
                    f"Small grid detected: only {active} of {max_cores} "
                    f"available cores are used. Consider increasing the "
                    f"block count to utilize more cores for better "
                    f"performance."
                ),
                [HintTarget(None, None, None, is_kernel=True)],
            )
        return self.result
