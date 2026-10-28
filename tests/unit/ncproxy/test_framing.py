from ncproxy import Framing, NetconfFramer, encode_message, split_messages


def test_base10_split_and_encode():
    msg = b"<hello/>"
    wire = encode_message(msg, Framing.BASE10)
    msgs, rem, framing = split_messages(wire)
    assert framing == Framing.BASE10
    assert msgs == [msg]
    assert rem == b""


def test_base11_chunk_length_bytes():
    msg = "ä".encode() * 10
    wire = encode_message(msg, Framing.BASE11, chunk_size=5)
    msgs, rem, framing = split_messages(wire)
    assert framing == Framing.BASE11
    assert msgs == [msg]
    assert rem == b""


def test_partial_chunk_buffered():
    wire = b"\n#5\n<hel"
    msgs, rem, framing = split_messages(wire)
    assert msgs == []
    assert framing == Framing.BASE11
    assert rem == wire


def test_base11_reassembled_across_feeds():
    msg = b"<rpc-reply>" + b"x" * 5000 + b"</rpc-reply>"
    wire = encode_message(msg, Framing.BASE11, chunk_size=4000)
    mid = len(wire) // 2
    framer = NetconfFramer()
    assert framer.feed(wire[:mid]) == []
    pairs = framer.feed(wire[mid:])
    assert len(pairs) == 1
    assert pairs[0][0] == msg
    assert pairs[0][1] == Framing.BASE11
