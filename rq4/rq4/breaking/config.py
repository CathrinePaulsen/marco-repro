from pathlib import Path

bump_benchmark = Path(__file__).parent.parent.parent.resolve() / "resources" / "bump_benchmark"

original_dataset = bump_benchmark / "original"
cleaned_dataset = bump_benchmark / "cleaned"

static_dataset = bump_benchmark / "static"
no_static_dataset = bump_benchmark / "no_static"
no_jar_dataset = bump_benchmark / "no_jar"

linked_dataset = bump_benchmark / "linked"
no_link_no_pom_dataset = bump_benchmark / "no_link" / "no_pom"
no_link_no_github_dataset = bump_benchmark / "no_link" / "no_github"
no_link_no_tag_dataset = bump_benchmark / "no_link" / "no_tag"

runnable_dataset = bump_benchmark / "runnable"
no_run_no_comp_dataset = bump_benchmark / "no_run" / "no_comp"
no_run_no_maven_dataset = bump_benchmark / "no_run" / "no_maven"
no_run_no_test_dataset = bump_benchmark / "no_run" / "no_test"
no_run_no_resolve_dataset = bump_benchmark / "no_run" / "no_resolve"

repo_path = bump_benchmark / "repos"
missing_jar_path = bump_benchmark / "missing_jars"
missing_pom_path = bump_benchmark / "missing_poms"
