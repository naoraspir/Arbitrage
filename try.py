# import pulp as p
# from gekko import GEKKO
#
# c_1=0
# c_matchbook=c_1
# c_2=0
# c_betfair=c_2
# a=290
# b=301
# x_max=13.22
# y_max=9.58265
#
#
# #
# # # Create a LP Maximization problem
# # Lp_prob = p.LpProblem('Problem', p.LpMaximize)
# #
# # x = p.LpVariable("x", 1, x_max)
# # y = p.LpVariable("y", 1, y_max)
# m = GEKKO(remote=False)
# m.options.LINEAR=1
# m.options.SOLVER=1
# x = m.Var(lb=1, ub=x_max)  # p.LpVariable("x1", 1, x_max,cat=p.LpInteger)
# y = m.Var(lb=1, ub=y_max)
# m_y=(b-1)*(1-c_1)
# m_x1=a-1
# m_x2=1-c_2
# m.Maximize(m_y * y - m_x1 * x + m_x2 * x - y)
# m.Equation(m_y * y - m_x1 * x >= 0)
# m.Equation(m_x2 * x - y >= 0)
# # m.Equation(m_y * y - m_x1 * x >= 0)
# # m.Equation(2 * (m_x2 * x - y) - (m_y * y - m_x1 * x) >= 0)
# # m.Equation(2 * (m_y * y - m_x1 * x) - (m_x2 * x - y) >= 0)
# m.Equation(y <= 5)
# m.Equation(m_x1 * x <= 5)
# m.solve(disp=False)
# x=x.value[0]
# y=y.value[0]
# # if lay in betfair wins:
# rev_if_betfair = (x * (1 - c_betfair))
# loss_if_betfair = y
# prof_net_if_betfair_wins = rev_if_betfair - loss_if_betfair
#
# # if back wins in matchbook
# rev_if_matchbook = ((y * b) - y) * (1 - c_matchbook)
# loss_if_matchbook = (a * x) - x
# prof_net_if_matchbook_wins = rev_if_matchbook - loss_if_matchbook
# print(str(x)+" ,"+str(y)+" ,"+str(m_y * y - m_x1 * x + m_x2 * x - y))
#
# # Objective Function
# Lp_prob += ((m_y*y)-(m_x1*x))+((m_x2*x)-y)
#
# # Constraints:
# Lp_prob += 2*(m_y*y)-(m_x1*x)-((m_x2*x)-y) >= 0
# Lp_prob += 2 * ((m_x2*x)-y)- ((m_y*y)-(m_x1*x))>= 0
#
# print(Lp_prob)
#
# status = Lp_prob.solve()   # Solver
# print(p.LpStatus[status])   # The solution status
#
# g=p.value(x)
#
# # Printing the final solution
# print(p.value(x), p.value(y), p.value(Lp_prob.objective))
# p.pulpTestAl
