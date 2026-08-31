"""R1-R7 常规稳健性检验（批量执行）。

设计对应作业 Part A 2.3。主回归基线：
digital = 0.12092, SE(firm cluster) = 0.00472, t = 25.6, N = 3240
（见 output/main_did_results.csv）。

输出：output/robustness/robustness_table_r1_r7.csv（各检验关键指标）
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import scipy.stats as sps
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "raw" / "digital_transformation_firm_panel.csv"
OUT = ROOT / "output"
ROBUST = OUT / "robustness"
ROBUST.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_FILE)
df["log_labor_productivity"] = np.log(df["labor_productivity"])

BASE = "log_tfp ~ digital + capital_intensity + C(firm_id) + C(year)"


def fit(formula, data, cluster_col):
    model = smf.ols(formula, data=data)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return model.fit(cov_type="cluster", cov_kwds={"groups": data[cluster_col]})


def winsorize(s, lo=0.01, hi=0.99):
    q1, q2 = s.quantile([lo, hi])
    return s.clip(q1, q2)


def r1():
    """R1 平行趋势正式检验：事件研究（处理组×相对年份虚拟变量）+ 处理前系数联合 Wald 检验。"""
    d = df.copy()
    ry = np.where(d["treated"] == 1, d["relative_year"].astype(int), -1)
    ks = [-4, -3, -2, 0, 1, 2, 3, 4]
    # 用不含负号的列名（pre4/pre3/pre2/post0/post1...），避免公式解析器把 - 当运算符
    label = {k: (f"pre{abs(k)}" if k < 0 else f"post{k}") for k in ks}
    for k in ks:
        d[label[k]] = ((d["treated"] == 1) & (ry == k)).astype(float)
    cols = [label[k] for k in ks]
    formula = "log_tfp ~ " + " + ".join(cols) + " + C(firm_id) + C(year)"
    res = fit(formula, d, "firm_id")
    pre = [label[k] for k in [-4, -3, -2]]
    if all(p in res.params.index for p in pre):
        b = res.params[pre].values
        V = res.cov_params().loc[pre, pre].values
        stat = float(b @ np.linalg.inv(V) @ b)
        dof = len(pre)
        pval = 1 - sps.chi2.cdf(stat, dof)
        fval = stat / dof
    else:
        fval, pval = np.nan, np.nan
    return {"R1_pre_joint_F": fval, "R1_pre_joint_p": pval}


def r2(n_reps=200, seed=42):
    """R2 安慰剂检验：随机伪处理组，重复 n_reps 次。"""
    rng = np.random.default_rng(seed)
    treated_ids = df.loc[df["treated"] == 1, "firm_id"].unique()
    n_t = len(treated_ids)
    all_ids = df["firm_id"].unique()
    ests = []
    for _ in range(n_reps):
        pseudo = set(rng.choice(all_ids, size=n_t, replace=False))
        d = df.copy()
        d["pseudo_digital"] = (d["firm_id"].isin(pseudo) & (d["year"] >= 2020)).astype(int)
        res = fit("log_tfp ~ pseudo_digital + capital_intensity + C(firm_id) + C(year)", d, "firm_id")
        ests.append(res.params["pseudo_digital"])
    ests = np.array(ests)
    return {
        "R2_pseudo_mean": ests.mean(),
        "R2_pseudo_sd": ests.std(),
        "R2_pseudo_p5": np.percentile(ests, 5),
        "R2_pseudo_p95": np.percentile(ests, 95),
        "R2_true_estimate": 0.12092,
    }


def r3():
    """R3 替换结果变量：log(labor_productivity)。"""
    res = fit("log_labor_productivity ~ digital + capital_intensity + C(firm_id) + C(year)", df, "firm_id")
    return {"R3_est": res.params["digital"], "R3_se": res.bse["digital"], "R3_p": res.pvalues["digital"]}


def r4():
    """R4 改变控制变量：①不加 ②加满 ③加 firm_size。"""
    specs = {
        "R4a_no_ctrl": "log_tfp ~ digital + C(firm_id) + C(year)",
        "R4b_full_ctrl": "log_tfp ~ digital + capital_intensity + export_share + soe + C(firm_id) + C(year)",
        "R4c_plus_size": "log_tfp ~ digital + capital_intensity + firm_size + C(firm_id) + C(year)",
    }
    out = {}
    for k, f in specs.items():
        res = fit(f, df, "firm_id")
        out[f"{k}_est"] = res.params["digital"]
        out[f"{k}_se"] = res.bse["digital"]
    return out


def r5():
    """R5 改变聚类层级：①industry ②province ③二维(firm+year)。"""
    out = {}
    res_i = fit(BASE, df, "industry")
    out["R5_cluster_industry_est"] = res_i.params["digital"]
    out["R5_cluster_industry_se"] = res_i.bse["digital"]
    res_p = fit(BASE, df, "province")
    out["R5_cluster_province_est"] = res_p.params["digital"]
    out["R5_cluster_province_se"] = res_p.bse["digital"]
    # 二维聚类：firm + year（使用 linearmodels）
    try:
        from linearmodels.panel import PanelOLS
        d = df.set_index(["firm_id", "year"])
        d["const"] = 1.0
        mod = PanelOLS(d["log_tfp"], d[["digital", "capital_intensity", "const"]],
                       entity_effects=True, time_effects=True)
        res = mod.fit(cov_type="clustered", cluster_entity=True, cluster_time=True)
        out["R5_cluster_twoway_est"] = res.params["digital"]
        out["R5_cluster_twoway_se"] = res.std_errors["digital"]
    except Exception as e:
        out["R5_cluster_twoway_note"] = f"linearmodels 不可用: {e}"
    return out


def r6():
    """R6 极端值处理：log_tfp 1%/99% winsorize。"""
    d = df.copy()
    d["log_tfp_w"] = winsorize(d["log_tfp"])
    res = fit("log_tfp_w ~ digital + capital_intensity + C(firm_id) + C(year)", d, "firm_id")
    return {"R6_winsor_est": res.params["digital"], "R6_winsor_se": res.bse["digital"], "R6_winsor_p": res.pvalues["digital"]}


def r7():
    """R7 样本调整：①剔电子 ②剔大/小5%企业 ③2018-2022 窗口。"""
    out = {}
    d1 = df[df["industry"] != "electronics"]
    res1 = fit(BASE, d1, "firm_id")
    out["R7_drop_electronics_est"] = res1.params["digital"]
    size_mean = df.groupby("firm_id")["firm_size"].mean()
    lo, hi = size_mean.quantile([0.05, 0.95])
    keep = size_mean[(size_mean >= lo) & (size_mean <= hi)].index
    d2 = df[df["firm_id"].isin(keep)]
    res2 = fit(BASE, d2, "firm_id")
    out["R7_drop_extreme_size_est"] = res2.params["digital"]
    d3 = df[(df["year"] >= 2018) & (df["year"] <= 2022)]
    res3 = fit(BASE, d3, "firm_id")
    out["R7_window_2018_2022_est"] = res3.params["digital"]
    return out


def main():
    summary = {}
    checks = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "R6": r6, "R7": r7}
    for name, fn in checks.items():
        try:
            summary.update(fn())
            print(f"[OK] {name}")
        except Exception as e:
            summary[name] = f"ERROR: {e}"
            print(f"[ERR] {name}: {e}")
    # 写结果
    pd.DataFrame([summary]).T.to_csv(ROBUST / "robustness_table_r1_r7.csv", header=False)
    print(f"\nWrote {ROBUST / 'robustness_table_r1_r7.csv'}")
    for k, v in summary.items():
        print(f"{k} = {v}")


if __name__ == "__main__":
    main()
