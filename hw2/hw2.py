#!/usr/bin/env python3
import re
import sys
from collections import Counter
from functools import lru_cache
from gzip import open as gzopen

def transliteration(russian):
    '''
    Return text transliterated with the scientific
    transliteration. Also lowercases.
    '''
    tr = {
        'а': 'a',
        'б': 'b',
        'в': 'v',
        'г': 'g',
        'д': 'd',
        'е': 'e',
        'ё': 'ë',
        'ж': 'ž',
        'з': 'z',
        'и': 'i',
        'і': 'i',
        'й': 'j',
        'к': 'k',
        'л': 'l',
        'м': 'm',
        'н': 'n',
        'о': 'o',
        'п': 'p',
        'р': 'r',
        'с': 's',
        'т': 't',
        'у': 'u',
        'ф': 'f',
        'х': 'x',
        'ц': 'c',
        'ч': 'č',
        'ш': 'š',
        'щ': 'šč',
        'ъ': 'ʺ',
        'ь': "'", #palatization
        'ы': 'y',
        'ь': 'ʹ',
        'э': 'è',
        'ю': 'ju',
        'я': 'ja',
        }
    return ''.join(tr.get(char.lower(), char) for char in russian)


def czech_processing(word):
    '''Preprocess a czech word.'''
    return (word
            # remove vowel length
            .replace('á', 'a')
            .replace('í', 'i')
            .replace('ó', 'o')
            .replace('ú', 'u')
            .replace('é', 'e')
            .replace('ý', 'y')
            .replace('ů', "u")
            # ch is x in Russian
            .replace('ch', 'x')
            # seperate palatisation (like in Russian)
            .replace('ň', "n'")
            .replace('č', "c'")
            .replace('ď', "d'")
            .replace('ě', "e")
            .replace('ř', "r'")
            .replace('ť', "t'")
            )


def substitution_cost(ruchar, cschar):
    '''
    Set the cost of replacements.
    One could do much more here (like saying changing voice is cheap).
    '''
    if (ruchar, cschar) in [('i','y'), ('g','h'), ('y', 'i')]:
        return 0
    return 1


@lru_cache(maxsize=8192)
def levenshtein(source, target):
    '''
    Return the Levenshtein distance.
    Recursive because readability,
    memoized because not terrible speed.
    '''
    # Return length of the other string if one is empty:
    if not source or not target:
        return len(source) + len(target)
    # Identity is free:
    if source[0] == target[0]:
        return levenshtein(source[1:], target[1:])
    # cost + distance
    insert = levenshtein(source, target[1:]) + 1
    delete = levenshtein(source[1:], target) + 1
    substitute = levenshtein(source[1:], target[1:]) + substitution_cost(source[0], target[0])
    return min(insert, delete, substitute)

def get_words(filename, *, gzipped=False):
    '''Read a set of words from a raw file.'''
    print("Reading words from", filename, file=sys.stderr)
    words = Counter()
    my_open = gzopen if gzipped else open
    with my_open(filename, 'rt') as f:
        if gzipped:
            # Russian
            words.update(line.rstrip().lower() for line in f if line.rstrip().isalpha())
        else:
            # Czech
            for line in f:
                # regex [^\W\d_]+ is a hacky way to get \p{L} without the regex module, i.e. alphabetic characters
                words.update(map(str.lower, re.findall(r'[^\W\d_]+', line, re.UNICODE)))
    return words


def translate_words(russian, czech, n=5000):
    '''
    Given two counters of words, yield mappings of the n-most frequent ones.
    '''
    print("Finding translations...", file=sys.stderr)
    sorted_czech = [word for word, count in czech.most_common()]
    i=0
    for r_word, _ in russian.most_common(n):
        i += 1
        print("On {}/{}".format(i, n), end='\r', file=sys.stderr)
        r_trans = transliteration(r_word)
        best = float("Inf")
        candidate = ''
        for c_word in sorted_czech:
            # skip impossible improvements
            if abs(len(c_word)-len(r_trans)) > best:
                continue
            dist = levenshtein(r_trans, czech_processing(c_word))
            if dist < best:
                candidate = c_word
                best = dist
            if dist == 0:
                break
        if best >= max(len(r_word),len(candidate)):
            # not a real translation.
            yield r_word, '', float("Inf")
        else:
            yield r_word, candidate, best


if __name__ == '__main__':
    # set to true to show words that we haven't found translations for
    print_empty = True
    czech = get_words("svejk_1_a_2.txt")
    russian = get_words("wiki.10M.gz", gzipped=True)
    with open("output.tsv", "w") as f:
        for ru, cs, score in translate_words(russian, czech, n=5000):
            if cs or print_empty:
                print(ru, cs, sep="\t", file=f)
