#! /usr/bin/env python
# coding:utf-8


from math import log
from chartype import Chartype


def load_phrase_model(modelfile: str) -> dict:
    phrasemodel = {}
    with open(modelfile) as f:
        for line in f:
            words, prob = line.rstrip().split("\t")
            prob = float(prob)
            w1, w2 = words.split(",")
            if w1 not in phrasemodel:
                phrasemodel[w1] = {}
            phrasemodel[w1][w2] = prob
    return phrasemodel


def load_bigram_model(modelfile: str) -> (dict, dict):
    unimodel = {}
    bimodel = {}
    with open(kovfig.bigram_model_file) as f:
        for line in f:
            words, prob = line.rstrip().split("\t")
            prob = float(prob)
            if " " in words:
                w0, w1 = words.split(" ")
                bimodel[(w0, w1)] = prob
            else:
                unimodel[words] = prob
    return unimodel, bimodel


def bigram_prob(
        w0: str,
        w1: str,
        unimodel: dict,
        bimodel: dict,
        lambda2: float=0.95,
        lambda1: float=0.95,
        unk_n: int=1e6):
    if (w0, w1) in bimodel:
        prob = lambda2 * bimodel[(w0, w1)]
    elif w1 in unimodel:
        prob = (1 - lambda2) * lambda1 * unimodel[w1]
    else:
        prob = (1 - lambda2) * (1 - lambda1) * (1 / unk_n)
    print(w0, w1, -log(prob))
    return -log(prob)


def phrase_prob(
        p1: str,
        p2: str,
        phrasemodel: dict,
        lambda1: float=0.95,
        unk_n: int=1e6):
    if p1 in phrasemodel and p2 in phrasemodel[p1]:
        prob = lambda1 * phrasemodel[p1][p2]
    else:
        prob = (1 - lambda1) * (1 / unk_n)
    return -log(prob)


def _search(
        sent_without_symbol: [str],
        unimodel: dict,
        bimodel: dict,
        phrasemodel: dict,
        start_symbol: str="<s>",
        end_symbol: str="</s>",
        max_len=100):

    sent = [start_symbol] + sent_without_symbol + [end_symbol]
    sent_len = len(sent)
    best = [dict() for _ in range(sent_len)]
    best[0][(start_symbol, (0, 0))] = 0
    before_pos = [dict() for _ in range(sent_len)]

    ch = Chartype()

    for curpos in range(sent_len - 1):
        next_start = curpos + 1
        for next_end in range(next_start, min(sent_len, next_start+max_len)):
            next_phrase = ''.join(sent[next_start:next_end+1])
            next_word = sent[next_start]
            #print(next_phrase)

            for (cur_phrase, (cur_start, cur_end)), prob in \
                    best[curpos].items():
                #cur_word = sent[cur_end]
                cur_key = (cur_phrase, (cur_start, cur_end))
                conv_w0 = cur_phrase[-1]

                # 候補にそのまま変換しないパタンがない場合
                # このとき, next_phrase == next_word
                if next_start == next_end and \
                        (next_phrase not in phrasemodel
                         or next_word not in phrasemodel[next_phrase]):
                    try:
                        conv_phrase = ch.full2half(next_phrase)
                    except:
                        conv_phrase = next_phrase
                        #print("error: failed to convert halfwidth katakana")
                    conv_w1 = conv_phrase[0]
                    next_key = (conv_phrase, (next_start, next_end))
                    next_prob = prob \
                        + bigram_prob(conv_w0, conv_w1, unimodel, bimodel) \
                        + phrase_prob(next_phrase, next_word, phrasemodel)
                    if next_key in best[next_end]:
                        if best[next_end][next_key] >= next_prob:
                            best[next_end][next_key] = next_prob
                            before_pos[next_end][next_key] = cur_key
                    else:
                        best[next_end][next_key] = next_prob
                        before_pos[next_end][next_key] = cur_key
                    #print("{} {}".format(cur_word, next_word))
                if next_phrase in phrasemodel:
                    for conv_phrase in phrasemodel[next_phrase]:
                        conv_w1 = conv_phrase[0]
                        next_key = (conv_phrase, (next_start, next_end))
                        #print("  {} {}".format(cur_word, next_word))
                        next_prob = prob \
                            + bigram_prob(conv_w0, conv_w1,
                                          unimodel, bimodel) \
                            + phrase_prob(next_phrase,
                                          conv_phrase,
                                          phrasemodel)
                        if next_key in best[next_end]:
                            if best[next_end][next_key] >= next_prob:
                                best[next_end][next_key] = next_prob
                                before_pos[next_end][next_key] = cur_key
                        else:
                            best[next_end][next_key] = next_prob
                            before_pos[next_end][next_key] = cur_key
    from pprint import pprint
    pprint(best)
    pprint(before_pos)
    #return best, before_pos

    # search best
    ans = []
    ind = sent_len - 1
    start = ind
    end = ind
    min_val = float("inf")
    min_key = ""
    for (key, (_, _)), val in best[ind].items():
        if min_val > val:
            print("{} => {}: {} => {}".format(min_key, key, min_val, val))
            min_key = key
            min_val = val
    ans.append(min_key)
    phrase, (start, end) = before_pos[ind][(min_key, (start, end))]
    ans.append(phrase)

    while end != 0:
        phrase, (start, end) = before_pos[end][(phrase, (start, end))]
        ans.append(phrase)

    ans.reverse()

    return ans


if __name__ == '__main__':

    import kovfig
    import sys

    # load models
    phrasemodel = load_phrase_model(kovfig.phrase_model_file)
    unimodel, bimodel = load_bigram_model(kovfig.bigram_model_file)

    ifd = open(sys.argv[1]) if len(sys.argv) >= 2 else sys.stdin
    for line in (_.rstrip() for _ in ifd):
        ans = _search(list(line), unimodel, bimodel, phrasemodel)
        print(''.join(ans))
