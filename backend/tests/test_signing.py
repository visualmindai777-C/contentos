from app.core.signing import signature, signed_url

# Mismo vector que cloudflare/src/signing.test.ts: Python firma, el Worker verifica.
VECTOR = ("s3cret", "contents/abc/video.mp4", 1_700_000_000, "80b226bf9e5c1af0e7412ac4b9caf2e58401d5af7d9948ceab3ae56417cd71eb")


def test_signature_matches_the_worker_test_vector():
    secret, key, exp, expected = VECTOR
    assert signature(secret, key, exp) == expected


def test_signed_url_shape_and_unsigned_fallback():
    url = signed_url("https://w.example/artifacts/", "contents/abc/video.mp4", "s3cret", 3600, now=1_699_996_400)
    assert url == f"https://w.example/artifacts/contents/abc/video.mp4?exp=1700000000&sig={VECTOR[3]}"
    assert signed_url("https://w.example/artifacts", "k", "", 3600) == "https://w.example/artifacts/k"
