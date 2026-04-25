import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from typing import Dict, List, Union

class StatsAnalyzer:
    """
    연구 가설 검증 및 Disclosure-Practice Gap의 상관관계를 도출하기 위한 통계 분석 모듈입니다.
    Pandas DataFrame을 입력받아 비모수적 차이 검정 및 회귀 분석을 수행합니다.
    """
    
    @staticmethod
    def chi_square_test(df: pd.DataFrame, group_col: str, target_col: str) -> Dict[str, float]:
        """
        1. 카이제곱 검정 (Chi-square test of independence)
        범주형 독립 변수(예: 산업군, 투자단계)와 이진 종속 변수(예: Under-disclosure 발생 여부) 간의 연관성을 검정합니다.
        """
        contingency_table = pd.crosstab(df[group_col], df[target_col])
        chi2, p_val, dof, expected = stats.chi2_contingency(contingency_table)
        
        return {
            "test": "Chi-square",
            "chi2_statistic": chi2,
            "p_value": p_val,
            "dof": dof,
            "significant": p_val < 0.05
        }

    @staticmethod
    def fishers_exact_test(df: pd.DataFrame, group_col: str, target_col: str) -> Dict[str, float]:
        """
        2. 피셔의 정확 검정 (Fisher's exact test)
        2x2 교차표에서 특정 셀의 기대빈도가 5 미만이어서 카이제곱 검정의 가정을 만족하지 못할 때 
        작은 표본에 대해 정확한 p-value를 산출합니다.
        """
        contingency_table = pd.crosstab(df[group_col], df[target_col])
        if contingency_table.shape != (2, 2):
            raise ValueError("Fisher's exact test requires exactly a 2x2 contingency table.")
            
        oddsratio, p_val = stats.fisher_exact(contingency_table)
        
        return {
            "test": "Fisher's Exact",
            "odds_ratio": oddsratio,
            "p_value": p_val,
            "significant": p_val < 0.05
        }

    @staticmethod
    def mann_whitney_u_test(df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, float]:
        """
        3. 맨-휘트니 U 검정 (Mann-Whitney U test)
        두 독립된 집단 간의 비모수적 연속형 변수 차이를 검정합니다. 
        예를 들어, "핀테크 기업 vs 비핀테크 기업" 간의 평균 삽입 트래커 개수 차이 분석에 사용됩니다.
        """
        groups = df[group_col].dropna().unique()
        if len(groups) != 2:
            raise ValueError(f"Mann-Whitney U test requires exactly 2 groups, found {len(groups)}.")
            
        group1_data = df[df[group_col] == groups[0]][value_col].dropna()
        group2_data = df[df[group_col] == groups[1]][value_col].dropna()
        
        stat, p_val = stats.mannwhitneyu(group1_data, group2_data, alternative='two-sided')
        
        return {
            "test": "Mann-Whitney U",
            "group1": groups[0],
            "group2": groups[1],
            "statistic": stat,
            "p_value": p_val,
            "significant": p_val < 0.05
        }

    @staticmethod
    def logistic_regression(df: pd.DataFrame, target_col: str, predictor_cols: List[str]) -> sm.discrete.discrete_model.BinaryResultsWrapper:
        """
        4. 로지스틱 회귀 분석 (Logistic Regression)
        기업의 여러 특성(예: 설립연차, 시리즈 단계, 직원 수 등)이 
        종속변수(Mismatch 위반 확률 등)에 미치는 영향을 다변량 모델링합니다.
        """
        # 결측치가 있는 행 제거
        clean_df = df[[target_col] + predictor_cols].dropna()
        
        # 범주형 변수를 위한 더미 변수 처리 및 상수항(Intercept) 추가
        X = pd.get_dummies(clean_df[predictor_cols], drop_first=True)
        # Statsmodels는 기본적으로 상수항이 없으므로 명시적 추가 필요
        X = sm.add_constant(X)
        y = clean_df[target_col].astype(int)
        
        model = sm.Logit(y, X)
        result = model.fit(disp=False)
        return result

    @staticmethod
    def spearman_correlation(df: pd.DataFrame, col1: str, col2: str) -> Dict[str, float]:
        """
        5. 스피어만 상관 계수 (Spearman rank-order correlation)
        두 연속형 또는 순서형 변수 간의 비선형적(순위 기반) 상관관계를 분석합니다. 
        예: 정책 텍스트의 복잡성(길이)과 관측된 트래커 개수 간의 상관관계.
        """
        clean_df = df[[col1, col2]].dropna()
        corr, p_val = stats.spearmanr(clean_df[col1], clean_df[col2])
        
        return {
            "test": "Spearman Correlation",
            "correlation_coefficient": corr,
            "p_value": p_val,
            "significant": p_val < 0.05
        }
