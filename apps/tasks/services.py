"""
Business logic: Critical Path Method (CPM) calculation.
Uses topological sort (Kahn's algorithm) + forward/backward pass.
networkx is used for the graph structure.
"""
from datetime import date, timedelta
from decimal import Decimal
import networkx as nx

from .models import Task, TaskDependency
from apps.projects.models import Project


class CPMCalculator:
    def __init__(self, project: Project):
        self.project = project
        self.tasks = list(project.tasks.filter(is_summary=False))
        self.deps = list(
            TaskDependency.objects.filter(
                predecessor__project=project
            ).select_related('predecessor', 'successor')
        )
        self.working_days = project.working_days or [1, 2, 3, 4, 5]
        self.holidays = set(
            project.holidays.values_list('date', flat=True)
        )

    def _next_working_day(self, d: date, delta_days: float) -> date:
        days = int(delta_days)
        current = d
        counted = 0
        direction = 1 if days >= 0 else -1
        while counted < abs(days):
            current += timedelta(days=direction)
            if current.isoweekday() in self.working_days and current not in self.holidays:
                counted += 1
        return current

    def _working_days_between(self, start: date, end: date) -> float:
        if start >= end:
            return 0
        count = 0
        current = start
        while current < end:
            if current.isoweekday() in self.working_days and current not in self.holidays:
                count += 1
            current += timedelta(days=1)
        return float(count)

    def calculate(self) -> dict:
        if not self.tasks:
            return {}

        task_map = {t.id: t for t in self.tasks}
        G = nx.DiGraph()
        for t in self.tasks:
            G.add_node(t.id)
        for dep in self.deps:
            if dep.predecessor_id in task_map and dep.successor_id in task_map:
                G.add_edge(dep.predecessor_id, dep.successor_id, dep=dep)

        try:
            order = list(nx.topological_sort(G))
        except nx.NetworkXUnfeasible:
            return {}

        # Forward pass
        es = {}  # early_start
        ef = {}  # early_finish
        for tid in order:
            task = task_map[tid]
            dur = float(task.planned_duration)
            preds = list(G.predecessors(tid))
            if not preds:
                es[tid] = task.planned_start
            else:
                max_ef = task.planned_start
                for pid in preds:
                    edge = G[pid][tid].get('dep')
                    dep_type = edge.dependency_type if edge else 'FS'
                    lag = float(edge.lag) if edge else 0
                    if dep_type == 'FS':
                        cand = self._next_working_day(ef[pid], lag)
                    elif dep_type == 'SS':
                        cand = self._next_working_day(es[pid], lag)
                    elif dep_type == 'FF':
                        cand_ef = self._next_working_day(ef[pid], lag)
                        cand = self._next_working_day(cand_ef, -dur)
                    else:  # SF
                        cand = self._next_working_day(ef[pid], lag - dur)
                    if cand > max_ef:
                        max_ef = cand
                es[tid] = max_ef
            ef[tid] = self._next_working_day(es[tid], dur)

        # Project finish date
        project_finish = max(ef.values(), default=self.project.end_date)

        # Backward pass
        ls = {}  # late_start
        lf = {}  # late_finish
        for tid in reversed(order):
            task = task_map[tid]
            dur = float(task.planned_duration)
            succs = list(G.successors(tid))
            if not succs:
                lf[tid] = project_finish
            else:
                min_ls = project_finish
                for sid in succs:
                    edge = G[tid][sid].get('dep')
                    dep_type = edge.dependency_type if edge else 'FS'
                    lag = float(edge.lag) if edge else 0
                    if dep_type == 'FS':
                        cand = self._next_working_day(ls[sid], -lag)
                    elif dep_type == 'SS':
                        cand = self._next_working_day(ls[sid] + timedelta(days=dur), -lag)
                    elif dep_type == 'FF':
                        cand = self._next_working_day(lf[sid], -lag)
                    else:
                        cand = self._next_working_day(ls[sid] + timedelta(days=dur), -lag)
                    if cand < min_ls:
                        min_ls = cand
                lf[tid] = min_ls
            ls[tid] = self._next_working_day(lf[tid], -dur)

        # Compute floats and mark critical
        results = {}
        tasks_to_update = []
        for tid in order:
            task = task_map[tid]
            total_float = self._working_days_between(es[tid], ls[tid])
            succs = list(G.successors(tid))
            if succs:
                free_float = min(
                    self._working_days_between(ef[tid], es[sid]) for sid in succs
                )
            else:
                free_float = 0.0
            auto_critical = total_float <= 0
            # Jugement manuel prioritaire ; sinon calcul automatique (CPM)
            is_critical = (
                task.critical_override
                if task.critical_override is not None
                else auto_critical
            )

            task.early_start = es[tid]
            task.early_finish = ef[tid]
            task.late_start = ls[tid]
            task.late_finish = lf[tid]
            task.total_float = Decimal(str(total_float))
            task.free_float = Decimal(str(free_float))
            task.is_critical = is_critical
            tasks_to_update.append(task)

            results[tid] = {
                'early_start': es[tid],
                'early_finish': ef[tid],
                'late_start': ls[tid],
                'late_finish': lf[tid],
                'total_float': total_float,
                'free_float': free_float,
                'is_critical': is_critical,
                'auto_critical': auto_critical,
            }

        Task.objects.bulk_update(
            tasks_to_update,
            ['early_start', 'early_finish', 'late_start', 'late_finish',
             'total_float', 'free_float', 'is_critical']
        )
        return results


def propagate_summary_dates(project: Project):
    """Recalculate planned_start/end/duration of summary tasks bottom-up from
    their children's *effective* dates: early_start/early_finish (the CPM's
    dependency-adjusted schedule) when available, falling back to
    planned_start/planned_end for children the CPM hasn't scheduled yet.

    Summary tasks are excluded from CPMCalculator, so without this fallback
    a summary bar would be built from its children's raw planned dates even
    when a dependency pushed a child's actual start/finish later — making
    the parent's rolled-up dates inconsistent with what the Gantt draws for
    its own children.
    """
    tasks = list(project.tasks.values(
        'id', 'parent_id', 'planned_start', 'planned_end',
        'early_start', 'early_finish', 'is_summary',
    ))
    task_map = {t['id']: t for t in tasks}
    children_map: dict = {}
    for t in tasks:
        if t['parent_id']:
            children_map.setdefault(t['parent_id'], []).append(t['id'])

    def eff_start(t):
        return t['early_start'] or t['planned_start']

    def eff_end(t):
        return t['early_finish'] or t['planned_end']

    def depth(tid):
        d, t = 0, task_map.get(tid)
        while t and t['parent_id']:
            d += 1
            t = task_map.get(t['parent_id'])
        return d

    summary_ids = sorted(
        [t['id'] for t in tasks if t['is_summary']],
        key=lambda tid: -depth(tid),
    )

    to_update = []
    for tid in summary_ids:
        child_ids = children_map.get(tid, [])
        if not child_ids:
            continue
        starts = [eff_start(task_map[cid]) for cid in child_ids if eff_start(task_map[cid])]
        ends = [eff_end(task_map[cid]) for cid in child_ids if eff_end(task_map[cid])]
        if not starts or not ends:
            continue
        new_start, new_end = min(starts), max(ends)
        # Mutate task_map so a grandparent summary task rolling up this one
        # sees its freshly-computed dates too (bottom-up, deepest first).
        task_map[tid]['planned_start'] = new_start
        task_map[tid]['planned_end'] = new_end
        to_update.append(Task(
            id=tid,
            planned_start=new_start,
            planned_end=new_end,
            planned_duration=(new_end - new_start).days + 1,
        ))

    if to_update:
        Task.objects.bulk_update(to_update, ['planned_start', 'planned_end', 'planned_duration'])


def recalculate_schedule(project: Project):
    """Full schedule recompute, in the order that keeps every date consistent:
    1) WBS/is_summary flags (CPMCalculator filters on is_summary),
    2) CPM early/late dates for non-summary tasks,
    3) summary-task rollup, which reads the early dates computed in step 2.
    """
    recalculate_wbs(project)
    CPMCalculator(project).calculate()
    propagate_summary_dates(project)


def recalculate_wbs(project: Project):
    """Recalculate wbs_code, level, is_summary, and order for all tasks (depth-first)."""
    tasks = list(project.tasks.order_by('order'))

    def get_children(parent_id):
        return [t for t in tasks if t.parent_id == parent_id]

    order_counter = [0]

    def walk(task_list, prefix):
        for i, task in enumerate(task_list, start=1):
            code = f'{prefix}{i}' if prefix else str(i)
            level = code.count('.') + (0 if not prefix else 1)
            children = get_children(task.id)
            task.wbs_code = code
            task.level = level
            task.is_summary = len(children) > 0
            task.order = order_counter[0]
            order_counter[0] += 1
            if children:
                walk(children, code + '.')

    walk([t for t in tasks if t.parent_id is None], '')
    Task.objects.bulk_update(tasks, ['wbs_code', 'level', 'is_summary', 'order'])
