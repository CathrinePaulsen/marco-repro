from pathlib import Path

import sqlalchemy
from sqlalchemy import func, distinct, Integer
from sqlalchemy.orm import Session

import rq12.models as models
from rq12.models import engine

path_to_repos = Path(__file__).parent.parent.resolve() / "resources" / "repos"


def get_results():
    with Session(engine) as session:
        projects = session.query(models.Project).filter(models.Project.compiles == sqlalchemy.true(),
                                                        models.Project.error == sqlalchemy.null())

        total_projects = len(projects.all())
        print(f"Total projects with compiles == 1, i.e. tree was made: {total_projects}")

        projects_with_deps = projects.filter(models.Project.dependencies.any())

        print(f"\nTotal projects with dependencies: {len(projects_with_deps.all())}")

        print(f"\n/////// START RQ1.1 /////////")
        projects_with_used_undeclared_deps = projects_with_deps.filter(
            models.Project.dependencies.any(used_undeclared=sqlalchemy.true()))
        print(f"Total projects with >0 direct transitive dep: {len(projects_with_used_undeclared_deps.all())}")

        amount = 0
        for p in projects_with_used_undeclared_deps:
            deps = [x for x in p.dependencies if x.used_undeclared == 1]
            amount += len(deps)
        avg = amount / len(projects_with_used_undeclared_deps.all())
        print(f"\nAvg direct transitives in total projects: {avg}")
        print(f"/////// END RQ1.1 /////////")

        print(f"/////// START RQ1.2 /////////")
        projects_with_conflicts = (projects
                                   .join(models.Dependency)
                                   .join(models.Conflict)
                                   )

        print(f"Total projects with >0 SoftVer conflict: {len(projects_with_conflicts.all())}")

        projects_with_unmanaged_conflicts = (projects
                                   .join(models.Dependency)
                                   .join(models.Conflict)
                                   .filter(models.Conflict.managed == sqlalchemy.false())
                                   )
        print(f"\nTotal projects with >0 SoftVer unmanaged conflict: {len(projects_with_unmanaged_conflicts.all())}")

        projects_with_managed_conflicts = (projects_with_conflicts.filter(models.Conflict.managed == sqlalchemy.true()))
        tot_proj_managed_conflicts = session.query(func.count(distinct(models.Conflict.project_name))) \
            .filter(models.Conflict.managed == 1) \
            .scalar()
        print(f"\nTotal projects with >0 SoftVer managed conflict: {len(projects_with_managed_conflicts.all())}")
        print(f"\nTotal projects with >0 SoftVer managed conflict (2): {tot_proj_managed_conflicts}")

        total_conflict_decs = len(session.query(models.Conflict).all())
        total_unman_decs = len(session.query(models.Conflict).filter(models.Conflict.managed == 0).all())
        total_man_decs = len(session.query(models.Conflict).filter(models.Conflict.managed == 1).all())
        print(f"\nThere are {total_conflict_decs} conflicting declarations (unmanaged={total_unman_decs}, managed={total_man_decs})")
        total_conflicts = len(session.query(models.Dependency).join(models.Conflict).all())
        total_unman = len(session.query(models.Dependency).join(models.Conflict).filter(models.Conflict.managed == 0).all())
        total_man = len(session.query(models.Dependency).join(models.Conflict).filter(models.Conflict.managed == 1).all())
        print(f"\nThere are {total_conflicts} conflicts (unmanaged={total_unman}, managed={total_man})")

        print(f"Avg SoftVer conflicts for projects with conflicts: {total_conflicts / len(projects_with_conflicts.all())}")

        dependencies_with_conflicts = session.query(models.Dependency).filter(models.Dependency.conflicts.any())
        print(f"\nAvg conflicts for dependencies with conflicts (total): {total_conflicts / len(dependencies_with_conflicts.all())}")


        print(f"/////// END RQ1.2 /////////")
        print(f"/////// START REMAINING /////////")
        resolved_deps_total = session.query(models.Dependency).all()
        print(f"\nAvg \#resolved deps per project (total): {len(resolved_deps_total) / len(projects_with_deps.all())}")

        declared_deps_total = len(resolved_deps_total)
        for d in resolved_deps_total:
            declared_deps_total += len(d.conflicts)

        print(f"There are {declared_deps_total} declared_deps_total and {len(projects_with_deps.all())} projects_with_deps")
        print(f"\nAvg \#declarations per project (total): {declared_deps_total / len(projects_with_deps.all())}")

        unmanaged_conflicts_total = session.query(models.Dependency).join(models.Conflict).filter(models.Conflict.managed == sqlalchemy.false())
        print(f"\nAvg \#unmanaged conflicts per project (total): {len(unmanaged_conflicts_total.all()) / len(projects_with_unmanaged_conflicts.all())}")
        print(f"\nAvg \#unmanaged conflicts declarations per project (total): {total_unman_decs / len(projects_with_unmanaged_conflicts.all())}")

        managed_conflicts_total = session.query(models.Dependency).join(models.Conflict).filter(models.Conflict.managed == sqlalchemy.true())
        print(f"\nAvg \#managed conflicts per project (total): {len(managed_conflicts_total.all()) / len(projects_with_managed_conflicts.all())}")
        print(f"\nAvg \#managed conflict declarations per project (total): {total_man_decs / tot_proj_managed_conflicts}")
