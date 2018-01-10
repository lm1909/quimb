import pytest

import numpy as np
from numpy.testing import assert_allclose

from quimb import (
    entropy_subsys,
    schmidt_gap,
    isherm,
    ispos,
)

from quimb.tensor import (
    MatrixProductState,
    MatrixProductOperator,
    align_TN_1D,
    MPS_rand_state,
    MPO_identity,
    MPO_identity_like,
    MPO_rand,
    MPO_rand_herm,
    MPO_ham_heis,
)


class TestMatrixProductState:

    def test_matrix_product_state(self):
        tensors = ([np.random.rand(5, 2)] +
                   [np.random.rand(5, 5, 2) for _ in range(3)] +
                   [np.random.rand(5, 2)])
        mps = MatrixProductState(tensors)
        assert len(mps.tensors) == 5
        nmps = mps.reindex_sites('foo{}', inplace=False, where=slice(0, 3))
        assert nmps.site_ind_id == "k{}"
        assert isinstance(nmps, MatrixProductState)
        assert set(nmps.outer_inds()) == {'foo0', 'foo1',
                                          'foo2', 'k3', 'k4'}
        assert set(mps.outer_inds()) == {'k0', 'k1',
                                         'k2', 'k3', 'k4'}
        mps.site_ind_id = 'foo{}'
        assert set(mps.outer_inds()) == {'foo0', 'foo1',
                                         'foo2', 'foo3', 'foo4'}
        assert mps.site_inds == ('foo0', 'foo1', 'foo2', 'foo3', 'foo4')
        assert mps.site_ind_id == 'foo{}'
        mps.show()

    @pytest.mark.parametrize("dtype", [float, complex, np.complex128,
                                       np.float64, 'raise'])
    def test_rand_mps_dtype(self, dtype):
        if dtype == 'raise':
            with pytest.raises(TypeError):
                MPS_rand_state(10, 7, dtype=dtype)
        else:
            p = MPS_rand_state(10, 7, dtype=dtype)
            assert p.site[0].dtype == dtype
            assert p.site[7].dtype == dtype

    def test_left_canonize_site(self):
        a = np.random.randn(7, 2) + 1.0j * np.random.randn(7, 2)
        b = np.random.randn(7, 7, 2) + 1.0j * np.random.randn(7, 7, 2)
        c = np.random.randn(7, 2) + 1.0j * np.random.randn(7, 2)
        mps = MatrixProductState([a, b, c], site_tag_id="I{}")

        mps.left_canonize_site(0)
        assert mps['I0'].shape == (2, 2)
        assert mps['I0'].tags == {'I0'}
        assert mps['I1'].tags == {'I1'}

        U = (mps['I0'].data)
        assert_allclose(U.conj().T @ U, np.eye(2), atol=1e-13)
        assert_allclose(U @ U.conj().T, np.eye(2), atol=1e-13)

        # combined two site contraction is identity also
        mps.left_canonize_site(1)
        ptn = (mps.H & mps) ^ ['I0', 'I1']
        assert_allclose(ptn['I1'].data, np.eye(4), atol=1e-13)

        # try normalizing the state
        mps['I2'] /= mps['I2'].norm()

        assert_allclose(abs(mps.H @ mps), 1.0)

    def test_right_canonize_site(self):
        a = np.random.randn(7, 2) + 1.0j * np.random.randn(7, 2)
        b = np.random.randn(7, 7, 2) + 1.0j * np.random.randn(7, 7, 2)
        c = np.random.randn(7, 2) + 1.0j * np.random.randn(7, 2)
        mps = MatrixProductState([a, b, c], site_tag_id="I{}")

        mps.right_canonize_site(2)
        assert mps['I2'].shape == (2, 2)
        assert mps['I2'].tags == {'I2'}
        assert mps['I1'].tags == {'I1'}

        U = (mps['I2'].data)
        assert_allclose(U.conj().T @ U, np.eye(2), atol=1e-13)
        assert_allclose(U @ U.conj().T, np.eye(2), atol=1e-13)

        # combined two site contraction is identity also
        mps.right_canonize_site(1)
        ptn = (mps.H & mps) ^ ['I1', 'I2']
        assert_allclose(ptn['I1'].data, np.eye(4), atol=1e-13)

        # try normalizing the state
        mps['I0'] /= mps['I0'].norm()

        assert_allclose(mps.H @ mps, 1)

    def test_rand_mps_left_canonize(self):
        n = 10
        k = MPS_rand_state(n, 10, site_tag_id="foo{}",
                           tags='bar', normalize=False)
        k.left_canonize(normalize=True)

        assert k.count_canonized() == (9, 0)

        assert_allclose(k.H @ k, 1)
        p_tn = (k.H & k) ^ slice(0, 9)
        assert_allclose(p_tn['foo8'].data, np.eye(10), atol=1e-13)

    def test_rand_mps_left_canonize_with_bra(self):
        n = 10
        k = MPS_rand_state(n, 10, site_tag_id="foo{}",
                           tags='bar', normalize=False)
        b = k.H
        k.left_canonize(normalize=True, bra=b)
        assert_allclose(b @ k, 1)
        p_tn = (b & k) ^ slice(0, 9)
        assert_allclose(p_tn['foo8'].data, np.eye(10), atol=1e-13)

    def test_rand_mps_right_canonize(self):
        n = 10
        k = MPS_rand_state(n, 10, site_tag_id="foo{}",
                           tags='bar', normalize=False)
        k.right_canonize(normalize=True)
        assert_allclose(k.H @ k, 1)
        p_tn = (k.H & k) ^ slice(..., 0)
        assert_allclose(p_tn['foo1'].data, np.eye(10), atol=1e-13)

    def test_rand_mps_right_canonize_with_bra(self):
        n = 10
        k = MPS_rand_state(n, 10, site_tag_id="foo{}",
                           tags='bar', normalize=False)
        b = k.H
        k.right_canonize(normalize=True, bra=b)
        assert_allclose(b @ k, 1)
        p_tn = (b & k) ^ slice(..., 0)
        assert_allclose(p_tn['foo1'].data, np.eye(10), atol=1e-13)

    def test_rand_mps_mixed_canonize(self):
        n = 10
        rmps = MPS_rand_state(n, 10, site_tag_id="foo{}",
                              tags='bar', normalize=True)

        # move to the center
        rmps.canonize(orthogonality_center=4)
        assert rmps.count_canonized() == (4, 5)
        assert_allclose(rmps.H @ rmps, 1)
        p_tn = (rmps.H & rmps) ^ slice(0, 4) ^ slice(..., 4)
        assert_allclose(p_tn['foo3'].data, np.eye(10), atol=1e-13)
        assert_allclose(p_tn['foo5'].data, np.eye(10), atol=1e-13)

        # try shifting to the right
        rmps.shift_orthogonality_center(current=4, new=8)
        assert_allclose(rmps.H @ rmps, 1)
        p_tn = (rmps.H & rmps) ^ slice(0, 8) ^ slice(..., 8)
        assert_allclose(p_tn['foo7'].data, np.eye(4), atol=1e-13)
        assert_allclose(p_tn['foo9'].data, np.eye(2), atol=1e-13)

        # try shifting to the left
        rmps.shift_orthogonality_center(current=8, new=6)
        assert_allclose(rmps.H @ rmps, 1)
        p_tn = (rmps.H & rmps) ^ slice(0, 6) ^ slice(..., 6)
        assert_allclose(p_tn['foo5'].data, np.eye(10), atol=1e-13)
        assert_allclose(p_tn['foo7'].data, np.eye(8), atol=1e-13)

    def test_can_change_data(self):
        p = MPS_rand_state(3, 10)
        assert_allclose(p.H @ p, 1)
        p.site[1].data = np.random.randn(200)
        assert abs(p.H @ p - 1) > 1e-13

    def test_can_change_data_using_subnetwork(self):
        p = MPS_rand_state(3, 10)
        pH = p.H
        p.add_tag('__ket__')
        pH.add_tag('__bra__')
        tn = p | pH
        assert_allclose((tn ^ ...), 1)
        assert_allclose(tn[('__ket__', 'I1')].data,
                        tn[('__bra__', 'I1')].data.conj())
        p.site[1].data = np.random.randn(200)
        assert abs((tn ^ ...) - 1) > 1e-13
        assert not np.allclose(tn[('__ket__', 'I1')].data,
                               tn[('__bra__', 'I1')].data.conj())

    def test_adding_mps(self):
        p = MPS_rand_state(10, 7)
        assert max(p['I4'].shape) == 7
        p2 = p + p
        assert max(p2['I4'].shape) == 14
        assert_allclose(p2.H @ p, 2)
        p += p
        assert max(p['I4'].shape) == 14
        assert_allclose(p.H @ p, 4)

    @pytest.mark.parametrize("method", ['svd', 'eig'])
    @pytest.mark.parametrize('cutoff_mode', ['abs', 'rel', 'sum2'])
    def test_compress_mps(self, method, cutoff_mode):
        n = 10
        chi = 7
        p = MPS_rand_state(n, chi)
        assert max(p['I4'].shape) == chi
        p2 = p + p
        assert max(p2['I4'].shape) == chi * 2
        assert_allclose(p2.H @ p, 2)
        p2.left_compress(method=method, cutoff=1e-6, cutoff_mode=cutoff_mode)
        assert max(p2['I4'].shape) == chi
        assert_allclose(p2.H @ p, 2)
        assert p2.count_canonized() == (n - 1, 0)

    def test_compress_mps_right(self):
        p = MPS_rand_state(10, 7)
        assert max(p['I4'].shape) == 7
        p2 = p + p
        assert max(p2['I4'].shape) == 14
        assert_allclose(p2.H @ p, 2)
        p2.right_compress()
        assert max(p2['I4'].shape) == 7
        assert_allclose(p2.H @ p, 2)

    @pytest.mark.parametrize("method", ['svd', 'eig'])
    def test_compress_trim_max_bond(self, method):
        p = MPS_rand_state(20, 20)
        p.compress(method=method)
        assert max(p['I4'].shape) == 20
        p.compress(max_bond=13, method=method)
        assert max(p['I4'].shape) == 13
        assert p.H @ p < 1.0

    def test_compress_form(self):
        p = MPS_rand_state(20, 20)
        p.compress('left')
        assert p.count_canonized() == (19, 0)
        p.compress('right')
        assert p.count_canonized() == (0, 19)
        p.compress(7)
        assert p.count_canonized() == (7, 12)
        p = MPS_rand_state(20, 20)
        p.compress('flat', absorb='left')
        assert p.count_canonized() == (0, 0)

    @pytest.mark.parametrize("method", ['svd', 'eig'])
    @pytest.mark.parametrize("form", ['left', 'right', 'raise'])
    def test_add_and_compress_mps(self, method, form):
        p = MPS_rand_state(10, 7)
        assert max(p['I4'].shape) == 7

        if form == 'raise':
            with pytest.raises(ValueError):
                p.add_MPS(p, compress=True, method=method,
                          form=form, cutoff=1e-6)
            return

        p2 = p.add_MPS(p, compress=True, method=method, form=form, cutoff=1e-6)
        assert max(p2['I4'].shape) == 7
        assert_allclose(p2.H @ p, 2)

    def test_subtract(self):
        a, b, c = (MPS_rand_state(10, 7) for _ in 'abc')
        ab = a.H @ b
        ac = a.H @ c
        abmc = a.H @ (b - c)
        assert_allclose(ab - ac, abmc)

    def test_subtract_inplace(self):
        a, b, c = (MPS_rand_state(10, 7) for _ in 'abc')
        ab = a.H @ b
        ac = a.H @ c
        b -= c
        abmc = a.H @ b
        assert_allclose(ab - ac, abmc)

    def test_schmidt_values_entropy_gap_simple(self):
        n = 12
        p = MPS_rand_state(n, 16)
        p.right_canonize()
        svns = []
        sgs = []
        for i in range(1, n):
            sgs.append(p.schmidt_gap(i, current_orthog_centre=i - 1))
            svns.append(p.entropy(i, current_orthog_centre=i))

        pd = p.to_dense()
        ex_svns = [entropy_subsys(pd, [2] * n, range(i)) for i in range(1, n)]
        ex_sgs = [schmidt_gap(pd, [2] * n, range(i)) for i in range(1, n)]
        assert_allclose(ex_svns, svns)
        assert_allclose(ex_sgs, sgs)

    @pytest.mark.parametrize("rescale", [False, True])
    def test_partial_trace(self, rescale):
        n = 10
        p = MPS_rand_state(n, 7)
        r = p.ptr(keep=[2, 3, 4, 6, 8], upper_ind_id='u{}',
                  rescale_sites=rescale)
        rd = r.to_dense()
        if rescale:
            assert r.lower_inds == ('u0', 'u1', 'u2', 'u3', 'u4')
            assert r.upper_inds == ('k0', 'k1', 'k2', 'k3', 'k4')
        else:
            assert r.lower_inds == ('u2', 'u3', 'u4', 'u6', 'u8')
            assert r.upper_inds == ('k2', 'k3', 'k4', 'k6', 'k8')
        assert_allclose(r.trace(), 1.0)
        assert isherm(rd)
        pd = p.to_dense()
        rdd = pd.ptr([2] * n, keep=[2, 3, 4, 6, 8])
        assert_allclose(rd, rdd)


class TestMatrixProductOperator:
    def test_matrix_product_operator(self):
        tensors = ([np.random.rand(5, 2, 2)] +
                   [np.random.rand(5, 5, 2, 2) for _ in range(3)] +
                   [np.random.rand(5, 2, 2)])
        mpo = MatrixProductOperator(tensors)

        mpo.show()
        assert len(mpo.tensors) == 5
        assert mpo.upper_inds == ('k0', 'k1', 'k2', 'k3', 'k4')
        assert mpo.lower_inds == ('b0', 'b1', 'b2', 'b3', 'b4')
        op = mpo ^ ...
        # this would rely on left to right contraction if not in set form
        assert set(op.inds) == {'k0', 'b0', 'k1', 'b1', 'k2', 'b2',
                                'k3', 'b3', 'k4', 'b4'}

    def test_add_mpo(self):
        h = MPO_ham_heis(12)
        h2 = h + h
        assert max(h2.site[6].shape) == 10
        h.lower_ind_id = h.upper_ind_id
        t = h ^ ...
        h2.upper_ind_id = h2.lower_ind_id
        t2 = h2 ^ ...
        assert_allclose(2 * t, t2)

    def test_adding_mpo(self):
        h = MPO_ham_heis(6)
        hd = h.to_dense()
        assert_allclose(h @ h.H, (hd @ hd.H).tr())
        h2 = h + h
        assert_allclose(h2 @ h2.H, (hd @ hd.H).tr() * 4)
        h2.right_compress()
        assert_allclose(h2 @ h2.H, (hd @ hd.H).tr() * 4)
        assert max(h2['I3'].shape) == 5

    def test_subtract_mpo(self):
        a, b = MPO_rand(13, 7), MPO_rand(13, 7)
        x1 = a.trace() - b.trace()
        assert_allclose(x1, (a - b).trace())
        a -= b
        assert_allclose(x1, a.trace())

    def test_expand_mpo(self):
        h = MPO_ham_heis(12)
        assert h.site[0].dtype == float
        he = h.expand_bond_dimension(13)
        assert h.site[0].dtype == float
        assert max(he.site[6].shape) == 13
        h.lower_ind_id = h.upper_ind_id
        t = h ^ ...
        he.upper_ind_id = he.lower_ind_id
        te = he ^ ...
        assert_allclose(t, te)

    def test_expand_mpo_limited(self):
        h = MPO_ham_heis(12)
        he = h.expand_bond_dimension(3)  # should do nothing
        assert max(he.site[6].shape) == 5

    def test_mpo_identity(self):
        k = MPS_rand_state(13, 7)
        b = MPS_rand_state(13, 7)
        o1 = k @ b
        i = MPO_identity(13)
        k, i, b = align_TN_1D(k, i, b)
        o2 = (k & i & b) ^ ...
        assert_allclose(o1, o2)

    @pytest.mark.parametrize("dtype", (complex, float))
    def test_mpo_rand_herm_and_trace(self, dtype):
        op = MPO_rand_herm(20, bond_dim=5, phys_dim=3, dtype=dtype)
        assert_allclose(op.H @ op, 1.0)
        tr_val = op.trace()
        assert tr_val != 0.0
        assert_allclose(tr_val.imag, 0.0, atol=1e-14)

    def test_mpo_rand_herm_trace_and_identity_like(self):
        op = MPO_rand_herm(20, bond_dim=5, phys_dim=3, upper_ind_id='foo{}')
        t = op.trace()
        assert t != 0.0
        Id = MPO_identity_like(op)
        assert_allclose(Id.trace(), 3**20)
        Id.site[0] *= 3 / 3**20
        op += Id
        assert_allclose(op.trace(), t + 3)

    def test_partial_tranpose(self):
        p = MPS_rand_state(8, 10)
        r = p.ptr([2, 3, 4, 5, 6, 7])
        rd = r.to_dense()

        assert isherm(rd)
        assert ispos(rd)

        rpt = r.partial_transpose([0, 1, 2])
        rptd = rpt.to_dense()

        upper_inds = tuple('b{}'.format(i) for i in range(6))
        lower_inds = tuple('k{}'.format(i) for i in range(6))
        outer_inds = rpt.outer_inds()
        assert all(i in outer_inds for i in upper_inds + lower_inds)

        assert isherm(rptd)
        assert not ispos(rptd)
