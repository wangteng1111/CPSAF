from __future__ import annotations

SOURCES = {
    "herrmann_paper": {
        "authority": "authoritative",
        "facts": {
            "scenes": 51,
            "stacks_per_scene": 10,
            "paper_total_stacks": 510,
            "paper_train_stacks": 460,
            "paper_test_stacks": 50,
            "patch_hw": [128,128],
            "stride": 40,
            "paper_train_patches": 387000,
            "paper_test_patches": 56800,
            "focus_states": 49,
            "focus_min_m": 0.102,
            "focus_max_m": 3.91,
            "gt": "median depth -> closest focus index in inverse-depth space",
            "filter": "median confidence of depth maps; exact numeric threshold not recovered from indexed authoritative text",
        },
        "citation": "Herrmann et al., CVPR 2020, Learning to Autofocus",
    },
    "learnaf_public_readme": {
        "authority": "authoritative-release-metadata",
        "facts": {
            "public_train_sweeps": 351,
            "public_test_sweeps": 47,
            "raw_pd_hw": [756,2016],
            "raw_up_pd_hw": [1512,2016],
            "raw_white_level": 1023,
        },
        "citation": "Official LearnAF Dataset Readme, last updated 2020-11-02",
    },
    "choi_supplement": {
        "authority": "authoritative",
        "facts": {
            "valid_patch_rule": "train/evaluate only valid patches where MVS confidence is over a threshold",
            "numeric_threshold_in_indexed_text": None,
            "known_label_error_modes": ["little/no texture", "focal breathing"],
        },
        "citation": "Choi et al., ICCV 2023 supplementary, Sec. B",
    },
    "zhu_paper": {
        "authority": "authoritative",
        "facts": {
            "patch_hw": [128,128],
            "stride": 96,
            "focus_states": 49,
            "train_examples": 3341163,
            "test_examples": 382445,
            "train_spatial_patches": 68187,
            "test_spatial_patches": 7805,
            "single_step_relative_target": {
                "exact": 0.330,
                "within1": 0.698,
                "within2": 0.826,
                "within4": 0.907,
                "MAE": 2.342,
                "RMSE": 6.339,
            },
        },
        "citation": "Zhu et al., CVPR 2025, Stabilizing and Accelerating Autofocus...",
    },
    "third_party_thresholds": {
        "authority": "non-authoritative-do-not-freeze",
        "facts": {
            "observed_values": [0.95, 0.98],
            "note": "Values appear in a third-party reimplementation / experimental archive and are not accepted as Herrmann/Zhu protocol evidence.",
        },
    },
}
