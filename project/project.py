from __future__ import division, print_function
import sys
from collections import defaultdict, Counter

class Trie(object):
    def __init__(self, is_root=True):
        '''
        Initialize the suffix trie.

        When using it normally, there is no need to set the is_root parameter,
        it is just used to select the most diverse gender if even the last
        letter has never been seen.

        Train the trie by calling the record method:

        >>> root = Trie()
        >>> root.record('pizza', 'f')
        >>> root.record('plaza', 'f')
        >>> root.record('palazzo', 'm')

        You can then query it by calling the guess method:

        >>> root.guess('scala')
        {'f': 1.0}

        If you're just interested in the most likely gender, use best_guess.
        Keep in mind that this is nondeterministic in case two genders are
        equally likely.

        >>> root.best_guess('scala')
        'f'

        The set of genders is left undefined on purpose, so this can be used
        for any interesting amount of genders (2, 3, 4, ...), or, in theory
        for things other than genders, if it would make sense (like Latin
        conjugation forms).

        You can also train a trie from a tsv file:

        >>> root = Trie.from_tsv_file("words.tsv")

        Finally, it is possible to evaluate the trie on a gold standard,
        in order to obtain an accuracy measure and a confusion matrix:

        >>> root.evaluate("gold_standard.tsv")
        ...

        Pass debug=True to the method to see the instances where the
        classifier fails.
        '''
        # "pointers" to connected nodes
        self.links = defaultdict(lambda: Trie(is_root=False))
        self.genders = Counter()
        self.is_root = is_root

    @property
    def total(self):
        '''Return the total amount this node has been "seen".'''
        return sum(self.genders.values())

    @property
    def probabilities(self):
        '''Return a dictionary of probabilities at this node.'''
        return {key: self.genders[key] / self.total if self.total else 0
                for key in self.genders}

    def record(self, word, gender):
        '''
        Record the occurrence of a word with a certain gender.

        This works by recursively calling record on the last letter until the
        word is empty.
        '''
        self.genders[gender] += 1
        if word:
            self.links[word[-1]].record(word[:-1], gender)

    @property
    def most_diverse_class(self):
        '''Return the class with the most gender diversity'''
        c = Counter()
        for final_letter in self.links:
            c.update(self.links[final_letter].probabilities)
        total = sum(c.values())
        return {key: value / total if total else 0 for key, value in c.items()}


    def guess(self, word):
        '''Return the probabilities of a certain word having the genders.'''

        if not self.total:
            return False

        next_node = self.links[word[-1]].guess(word[:-1]) if word else False

        if next_node:
            return next_node
        elif not self.is_root:
            return self.probabilities
        else:
            return self.most_diverse_class

    def best_guess(self, word):
        '''
        Return the most likely gender for a given word.

        Note that this is non-deterministic if two genders are equally likely
        (it will choose one of the two).
        '''
        probabilities = self.guess(word)
        return max((key for key in probabilities), key=lambda x: probabilities[x])

    @staticmethod
    def from_tsv_file(filename, types=False, sep='\t'):
        '''
        Initialize a trie by reading the genders from a tsv file.

        If types is True, work on types, not tokens.
        '''
        root = Trie()
        seen = set()
        with open(filename) as f:
            for line in f:
                word, gender = line.rstrip().split(sep)
                if not types or word not in seen:
                    root.record(word, gender)
                    if types:
                        seen.add(word)
        return root

    def evaluate(self, filename, sep='\t', debug=False):
        '''
        Evaluate the trie based on a corpus file.

        Set debug to True to see the cases where it misclassifies words.
        '''
        guesses = defaultdict(Counter)
        with open(filename) as f:
            for line in f:
                word, gender = line.rstrip().split(sep)
                best_guess = self.best_guess(word)
                guesses[gender][best_guess] += 1
                if debug and gender != best_guess:
                    print("System classified {} as {}, but it is {}".format(word, best_guess, gender))
        print("guess->\t" + "\t".join(sorted(self.genders)))
        for gender in sorted(self.genders):
            print(gender, "\t".join(str(guesses[gender][guess]) for guess in sorted(self.genders)), sep="\t")

        print()

        total = sum(sum(guesses[gender].values()) for gender in self.genders)
        correct = sum(guesses[gender][gender] for gender in self.genders)
        print("Accuracy: {:.2f}% ({}/{})".format(100*correct/total, correct, total))


if __name__ == '__main__':
    # interactive demo
    if len(sys.argv) != 2:
        print("Usage: python3 project.py <filename>", file=sys.stderr)
        sys.exit(1)
    root = Trie.from_tsv_file(sys.argv[1])

    print("(Press Ctrl+D to exit)")
    try:
        while True:
            word = input("Enter a word to guess its gender: ")
            best, probs = root.best_guess(word), root.guess(word)
            print("Most likely gender: {} ({})".format(best, probs))
    except EOFError:
        pass
