from dogwhistle.stats import bootstrap_lower, sign_flip_one_sided


def test_exact_sign_flip_boundaries():
    assert sign_flip_one_sided([1, 1, 1]) == 1 / 8
    assert sign_flip_one_sided([0, 0]) == 1
    assert sign_flip_one_sided([-1, -1, -1]) == 1


def test_bootstrap_is_deterministic():
    assert bootstrap_lower([0.01, -0.01, 0.02], replications=100) == \
        bootstrap_lower([0.01, -0.01, 0.02], replications=100)
