import numbers

"""
Tableau method for Lquant
requires Python 3.11 (because we use matching)
"""

############## declaration of constants for the software

MAX = 4
RANGE = range(-MAX, MAX+1) # numbers that are guessed are integers between -MAX and MAX
LOGGING = True # True/False if you want to see the execution in the teminal


######### quantization function ###############

def testSum(a, b, s):
    return max(-MAX, min(MAX, a+b)) == s
    
############### deterministic rules ####################
"""Det rules modifies the current tableau T in place.
The rule returns true iff a modification was made.
Adding False to T will make the tableau inconsistent (clash)
"""

def ruleAnd(T):
    for e in T:
        match e:
            case (w, (p, "and", q)):
                T.remove((w, (p, "and", q)))
                T.add((w, p))
                T.add((w, q))
                return True


def ruleNot(T):
    for e in T:
        match e:
            case (w, ("not", (e, ">=", v))):
                T.remove((w, ("not", (e, ">=", v))))
                T.add((w, (("*", -1, e), ">=", -v)))
                return True


def ruleC(T):
    for e in T:
        match e:
            case (w, (("*", c, e), "=", v)):
                T.remove((w, (("*", c, e), "=", v)))
                resultDiv = v // c
                if resultDiv > MAX:
                    resultDiv = MAX 
                if resultDiv < -MAX:
                    resultDiv = -MAX 

                if resultDiv * c == v:
                    T.add((w, (e, "=", resultDiv)))
                else:
                    T.add(False)
                return True


def ruleReLUDet(T):
    for e in T:
        match e:
            case (w, (("ReLU", e), "=", v)):
                if v > 0:
                    T.remove((w, (("ReLU", e), "=", v)))
                    T.add((w, (e, "=", v)))
                    return True



"""Clash rules returns true if a modification was made, i.e. if there is a clash.
"""
def ruleClashEq(T):
    for e in T:
        match e:
            case (w, (p, "=", v)):
                for e2 in T:
                    match e2:
                        case (w2, (p2, "=", v2)) if w == w2 and p == p2:
                            if v != v2:
                                T.add(False)
                                return True

def ruleClashC(T):
    for e in T:
        match e:
            case (w, (c, "=", k)):
                if isinstance(c, numbers.Number) and c != k:
                    T.add(False)
                    return True
                

############# non-deterministic rules 
"""ND rules takes the current tableau and may create branches in sets.
Again, it returns true if a modification was made.
"""


def ruleMinus(T, sets):
    for e in T:
        match e:
            case (w, ((e1, "-", e2), "=", v)):
                T.remove((w, ((e1, "-", e2), "=", v)))
                for e1v in RANGE:
                    for e2v in RANGE:
                        if testSum(e1v, -e2v, v):
                            sets.appendBranch(
                                {*T, (w, (e1, "=", e1v)), (w, (e2, "=", e2v))})
                return True

def ruleAdd(T, sets):
    for e in T:
        match e:
            case (w, ((e1, "+", e2), "=", v)):
                T.remove((w, ((e1, "+", e2), "=", v)))
                for e1v in RANGE:
                    for e2v in RANGE:
                        if testSum(e1v, e2v, v):
                            sets.appendBranch(
                                {*T, (w, (e1, "=", e1v)), (w, (e2, "=", e2v))})
                return True
            

def ruleGeq(T, sets):
    for e in T:
        match e:
            case (w, (p, ">=", v)):
                T.remove((w, (p, ">=", v)))
                for i in range(v, MAX):
                    sets.appendBranch({*T, (w, (p, "=", i))})
                return True


def ruleAgg(T, sets):
    for e in T:
        match e:
            case (w, (("agg", e), "=", v)):
                T.remove((w, (("agg", e), "=", v)))
                for v1 in RANGE:
                  #  for v2 in range(-MAX, MAX):
                        #if v1 + v2 == v:
                    v2 = v - v1
                    if v2 in RANGE:
                        sets.appendBranch(
                                {*T, (w*10+1, (e, "=", v1)), (w*10+2, (e, "=", v2))})
                return True


            

def ruleReLU(T, sets):
    for e in T:
        match e:
            case (w, (("ReLU", e), "=", v)):
                T.remove((w, (("ReLU", e), "=", v)))
                if v <= 0:
                    for i in range(-MAX, 0):
                        sets.appendBranch({*T, (w, (e, "=", i))})
                    return True



"""
The data structure that contains many tableaux
"""
class ComputationTree:
    """creates a computation tree with an initial set for the single tableau
    e.g. CT = new ComputationTree({(0, ("p", "and", "q"))})
    """
    def __init__(self, initialSet):
        print("initialization: ", initialSet)
        self.sets = [initialSet] #the data structure is just a Python list :)

    def applyDetRule(self, rule):
        for T in self.sets:
            if rule(T):
                if LOGGING:
                    print("apply", rule.__name__, ":",  T)
                if False in T: # remove inconsistent tableaux
                    self.sets.remove(T)
                return True

    def applyNDRule(self, rule):
        for T in self.sets:
            if rule(T, self):
                self.sets.remove(T)
                return True

    def applySomeRuleD(self, rules):
        for R in rules:
            if self.applyDetRule(R):
                return True

    def applySomeRuleND(self, rulesND):
        for R in rulesND:
            if self.applyNDRule(R):
                return True


    """main loop of the tableau method
    Then priority to deterministic rules which are not so dangerous
       (some "clash" rules may add False and then it means that the current tableau becomes inconsistent)
    Then less priority to non-deterministic rules which are dangerous because of branching
    """
    def applyRules(self, detRules, nondetRules):
        while True:
            if self.applySomeRuleD(detRules):
                continue
            if not self.applySomeRuleND(nondetRules):
                break


        print("no more rules applicable")
        if not self.sets:
            print("no tableau")
        else:
            print("example of final tableau:", self.sets[0])

        return

    """(used by the ND rules. It adds the new tableau newT to the collection of tableaux)
    """
    def appendBranch(self, newT):
        if LOGGING:
            print("new branch: ", newT)
        self.sets.append(newT)




"""main procedure.
We create a formula of Lquant
We initialize the computation tree for the tableau method
We launch the tableau method
"""
def main():
    phiIn = (("agg", "x1"), ">=", 1)
    phiN = (
        ((("ReLU", ("*", 2, "x1")), "-", "y1"), "=", 0),
        "and",
        ((("*", 2, ("agg", "x1")), "-", "y2"), "=", 0)
    )
    phiOut = ("y1", ">=", 1)
    phi = ((phiIn, "and", phiN), "and", ("not", phiOut))

    INITIALVERTEX = 1
    CT = ComputationTree({(INITIALVERTEX, phi)})
    CT.applyRules([ruleClashEq, ruleClashC, ruleAnd, ruleNot, ruleC, ruleReLUDet],
                [ruleGeq, ruleMinus, ruleAdd, ruleReLU, ruleAgg])

if __name__ == '__main__':
    main() # run the program if not imported
