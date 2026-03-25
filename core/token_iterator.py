class TokenIterator(object):
    def __init__(self, tokens):
        self.tokens = iter(tokens)

    def until(self, end):
        tokens = []
        while True:
            token = self.__next__()
            tokens.append(token)
            if token != end:
                continue

            backslash_count = 0
            idx = len(tokens) - 2
            while idx >= 0 and tokens[idx] == '\\':
                backslash_count += 1
                idx -= 1

            if backslash_count % 2 == 0:
                return tokens

    def __next__(self):
        token = next(self.tokens)
        while token == '':
            token = next(self.tokens)
        return token
