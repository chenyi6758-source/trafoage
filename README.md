# trafoage

[![tests: 29 passed](https://img.shields.io/badge/tests-29%20passed-brightgreen.svg)](tests/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)

**English** | [简体中文](#trafoage-中文)

**How fast does a distribution transformer age when PV, EVs and heat pumps move in?** `trafoage` answers with the IEEE Std C57.91-2011 transient thermal model and insulation aging law, wired to DER loading scenarios and optionally to pandapower time-series results.

## Results at a glance

200 kVA ONAN transformer, 120 kW residential peak, one simulated day per scenario:

![loading and hot-spot by scenario](examples/quickstart_loading_hotspot.png)
![daily life consumption by scenario](examples/quickstart_aging.png)

| scenario | F_EQA | life consumed / day | max hot-spot | time > 110 °C |
|---|---|---|---|---|
| base (no DER) | 0.001 | 0.02 h | 56.0 °C | 0% |
| + 120 kW PV | 0.001 | 0.02 h | 61.1 °C | 0% |
| + 90 kW EV charging | 0.007 | 0.16 h | 82.4 °C | 0% |
| PV + EV | 0.007 | 0.16 h | 82.2 °C | 0% |
| winter: heat pump + EV | 0.194 | 4.64 h | 115.4 °C | 9.4% |

Three findings worth a planner's attention:

1. **EV home charging dominates aging here** — 7× the base-case life consumption, because it stacks on the evening peak when the transformer is already warm.
2. **PV barely offsets EV-driven aging** — the two peak at different hours. Counter-intuitively, midday hot-spot is *slightly higher* with PV (61.1 vs 56.0 °C): 120 kW of PV pushes 0.41 pu of reverse flow, more current than the midday load it displaced. Windings heat on |current|, not on direction.
3. **A cold winter day with heat pumps + EV is the killer** — 4.64 h of insulation life per day, 194× the base case. Sustained, that pace would eat the 20.5-year normal insulation life far early. (One-day scenario, not a yearly claim — see honesty notes.)

## Problem

Hosting-capacity studies (including my [pvhostcap](https://github.com/chenyi6758-source/pvhostcap) and [pvhost-prob](https://github.com/chenyi6758-source/pvhost-prob)) answer "how much DER fits before a *limit* is violated". Utilities also need the slower question: **what does the DER mix do to asset life?** Distribution transformers are the most numerous grid asset, lead times stretched to 12–30 months in 2023, and recent work (Poore et al., IEEE ECCE 2024) shows new loads are rewriting their service factors. Yet there is no packaged, tested, open-source tool that turns a loading profile into IEEE C57.91 hot-spot temperatures and loss-of-life — only scattered scripts and spreadsheet implementations. `trafoage` is that tool.

## Method

**Thermal model** (`trafoage/thermal.py`). IEEE Std C57.91-2011 for mineral-oil-immersed transformers: top-oil rise and hot-spot rise over top-oil each follow first-order dynamics toward load-dependent ultimate values, with the guide's load-corrected top-oil time constant. Defaults are literature-typical ONAN distribution-transformer values (Δθ_TO,R = 55 °C, Δθ_H,R = 25 °C, R = 5, n = m = 0.8, τ_TO,R = 3 h, τ_W = 5 min); every one is overridable from your test report.

**Aging law** (`trafoage/aging.py`). The guide's Arrhenius form anchored at the 110 °C reference (F_AA = 1 by definition), equivalent aging factor F_EQA, and % loss of life against the 180,000 h normal insulation life.

**DER scenarios** (`trafoage/scenarios.py`). Documented synthetic shapes — residential evening peak, PV bell, EV home-charging hump, winter heat-pump load — scaled by *your* kW assumptions. Reverse power flow is handled by |k|: export heats windings just like import.

**Grid link** (`trafoage/pandapower_link.py`, optional). Feed a pandapower network + time series through `loading_from_timeseries()` and get per-unit transformer loading straight into the thermal model. This is the bridge to the hosting-capacity tools: screen with pvhostcap/pvhost-prob, then price the transformer life.

## Quickstart

```bash
pip install trafoage          # once published; for now: pip install .
python examples/quickstart.py # one command: 5 scenarios, 2 plots, 1 table
```

Or the CLI:

```bash
trafoage --compare
trafoage --scenario winter-hp --out results/
```

```python
from trafoage import Transformer, simulate, faa, summarize
from trafoage.scenarios import hours_of_day, make_loading, ambient_daily

h = hours_of_day()                       # 96 steps, 15-min
k = make_loading(h, trafo_kva=200, base_peak_kw=120,
                 pv_kw=120, ev_kw=90)    # signed pu loading
tr = Transformer(nameplate_kva=200)
out = simulate(k, ambient_daily(h), tr, dt_h=0.25)
print(summarize(faa(out["theta_h"]), out["theta_h"], dt_h=0.25))
```

## Validation

- Defining identities of the standard hold exactly: F_AA(110 °C) = 1, rated load + 30 °C ambient → 110 °C hot-spot, 24 h at rated load consumes ≈ 24 h of the 180,000 h normal life.
- Time-step refinement converges (1 h vs 15 min vs 7.5 min agree to < 0.2 °C end-aligned).
- Reverse flow heats identically to forward flow at the same |k|.
- 29 pytest tests (27 core + 2 pandapower bridge against a real `pp.runpp` time series).

## Honesty notes

- Scenario *shapes* are synthetic and documented; magnitudes are caller inputs. The tool quantifies thermal consequences of *assumed* profiles — it does not measure your feeder.
- Thermal defaults are literature-typical, not your transformer's test report. For investment decisions, plug in measured Δθ_TO,R, Δθ_H,R, R and time constants.
- Harmonics from PV inverters add stray loss the C57.91 fundamental-current model does not capture (see Wazir et al. below) — treat high-harmonic cases as a lower bound on aging.

## References

- IEEE Std C57.91-2011, *IEEE Guide for Loading Mineral-Oil-Immersed Transformers and Step-Voltage Regulators* — thermal model and aging law.
- S. B. Poore, R. E. Alden, T. Rooney & D. M. Ionel, "New Loads and Service Factors for Distribution Transformers Following the Transition to High-Efficiency Heat Pumps, Solar PV, and EV Charging," *Proc. IEEE ECCE 2024*. https://sparklab.engr.uky.edu/sites/spark/files/2026-01/2024_ECCE_Conference_Paper_Transformer_Loading.pdf
- M. H. M. Wazir et al., "On the Effects of Solar Panels on Distribution Transformers" — PV-harmonic electro-thermal modelling vs IEEE C57.110. https://www.researchgate.net/publication/281182969_On_the_Effects_of_Solar_Panels_on_Distribution_Transformers
- "Quantifying Overload Risk: A Parametric Comparison of IEC 60076-7 and IEEE C57.91 Standards for Power Transformers," *Energies* 2025. https://www.mdpi.com/1996-1073/18/24/6469
- "Analyzing the Impact of Ambient Temperature Indicators on Transformer Life in Different Regions of Chinese Mainland" (IEEE C57.91-1995 life-consumption model). https://pmc.ncbi.nlm.nih.gov/articles/PMC3697416/

---

## trafoage 中文

**配变在光伏、电动车、热泵进来之后，老化有多快？** `trafoage` 用 IEEE Std C57.91-2011 的暂态热模型和绝缘老化定律来回答，输入可以是内置的 DER 场景，也可以是 pandapower 时序仿真结果。

上面英文部分的表格和两张图就是一键运行的结果（`python examples/quickstart.py`），结论三句话：

1. **家用充电桩是老化主力**——叠加在本来就热的晚高峰上，日寿命损耗是无 DER 基准的 7 倍；
2. **光伏几乎对冲不掉电动车的老化**——两者高峰不在同一个时段。反直觉的是，加了光伏之后正午热点温度反而略升（61.1 vs 56.0 °C）：120 kW 光伏造成 0.41 pu 的反向潮流，电流比被它顶掉的正午负荷还大，而绕组发热只看电流大小、不看方向；
3. **冬天热泵 + 电动车最要命**——一天吃掉 4.64 小时绝缘寿命，是基准的 194 倍，热点 9.4% 的时间超过 110 °C。

为什么做这个：接纳能力工具（我的 [pvhostcap](https://github.com/chenyi6758-source/pvhostcap) / [pvhost-prob](https://github.com/chenyi6758-source/pvhost-prob)）回答"DER 装多少会越限"，但电网公司同样需要慢变量——**DER 结构变化对资产寿命的影响**。配变是电网数量最多的资产，2023 年订货周期曾拉长到 12–30 个月，而开源社区里一直没有一个打包好、有测试的 IEEE C57.91 工具，只有零散脚本。`trafoage` 就是补这个空白的。

快速开始、方法、验证与英文部分一致。诚实说明：场景形状是文献化的合成曲线、量级由调用者给定；热参数默认值是文献典型值，做投资决策请换实测铭牌/试验值；逆变器谐波带来的杂散损耗不在 C57.91 基波模型内，高谐波场合本工具给出的是老化下限。
