package com.example.maven;

import org.apache.maven.AbstractMavenLifecycleParticipant;
import org.apache.maven.execution.MavenSession;
import org.apache.maven.model.Dependency;
import org.apache.maven.project.MavenProject;

import java.util.List;

public class VersionReplacementExtension extends AbstractMavenLifecycleParticipant {

    @Override
    public void afterProjectsRead(MavenSession session) {
        System.out.println("My extension is active!");
        List<MavenProject> projects = session.getProjects();

        for (MavenProject project : projects) {
            List<Dependency> dependencies = project.getDependencies();

            for (Dependency dependency : dependencies) {
                // Replace versions with ranges based on your custom logic
                String originalVersion = dependency.getVersion();
                String newVersionRange = convertToVersionRange(originalVersion);
                dependency.setVersion(newVersionRange);
            }
        }
    }

    private String convertToVersionRange(String version) {
        // Your custom logic to convert a version to a version range
        // For simplicity, let's assume adding "[,)" to the version
//        return "[" + version + ",)";
        return "404";
    }
}