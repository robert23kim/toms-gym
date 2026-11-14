import sys
root = sys.argv[1]
p = root + '/src/lifting/pose/parallel.py'
s = open(p).read()
rep = [
('''def _find_sync(owner: ChunkStream, cand: ChunkStream, sync_frames: int) -> int | None:
    """First frame where cand matches owner on sync_frames consecutive frames."""
    run = 0
    for f in range(max(cand.start, owner.start), min(owner.hi, cand.hi)):
''', '''def _find_sync(owner: ChunkStream, cand: ChunkStream, sync_frames: int, start: int) -> int | None:
    """First frame >= start where cand matches owner on sync_frames consecutive frames."""
    run = 0
    for f in range(max(cand.start, owner.start, start), min(owner.hi, cand.hi)):
'''),
('''        f = _find_sync(owner, cand, sync_frames)
        while f is None and not owner.eof and owner.hi < cand.hi:
            owner.extend(min(max(owner.hi, cand.start) + extend_step, cand.hi))
            f = _find_sync(owner, cand, sync_frames)
''', '''        f = _find_sync(owner, cand, sync_frames, cursor)
        while f is None and not owner.eof and owner.hi < cand.hi:
            owner.extend(min(max(owner.hi, cand.start) + extend_step, cand.hi))
            f = _find_sync(owner, cand, sync_frames, cursor)
'''),
('''    adopted from its first verified sync frame; until then the current owner is
    extended, and a stream that never syncs is dropped.
''', '''    adopted from its first verified sync frame; until then the current owner is
    extended, and a stream that never syncs is dropped. The owner is only true from
    its own sync frame (cursor) on, so the search never starts before it: two cold
    chunks agree with each other without either being right.
'''),
]
for a, b in rep:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(p, 'w').write(s)

t = root + '/tests/test_lifting/test_pose_parallel.py'
s = open(t).read()
rep = [
('''    def __init__(self, start, total, resync=0, initial_hi=None, coincide=()):
        super().__init__(start)
''', '''    def __init__(self, start, total, resync=0, initial_hi=None, coincide=(), cold_tag=None):
        super().__init__(start)
        self.cold_tag = cold_tag or f"cold{start}"
'''),
('''            self.records.append((f"t{k}" if true else f"cold{self.start}-{k}", k))
''', '''            self.records.append((f"t{k}" if true else f"{self.cold_tag}-{k}", k))
'''),
('''    def test_dropped_chunk_then_late_sync_on_the_next(self):
''', '''    def test_two_cold_chunks_agreeing_is_not_a_sync(self):
        # Chunk 1 only turns true at 405, past the next bound. Before that it and
        # chunk 2 both show the detector-only output, so they agree at 400..404.
        streams = [FakeStream(0, 600, initial_hi=208),
                   FakeStream(200, 600, resync=205, initial_hi=408, cold_tag="cold"),
                   FakeStream(400, 600, resync=50, cold_tag="cold")]
        records, offsets = splice_streams(streams, sync_frames=2)
        assert records == _truth(600)
        assert offsets == [205, 50]

    def test_dropped_chunk_then_late_sync_on_the_next(self):
'''),
]
for a, b in rep:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
open(t, 'w').write(s)
print("patched", root)
