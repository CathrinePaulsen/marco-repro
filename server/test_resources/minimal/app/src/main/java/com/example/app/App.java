package com.example.app;

import com.example.dep.Dep;

/**
 * Hello world!
 *
 */
public class App
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from App!" );
        Dep.method("App");
    }

    public static void method(String from) {
        System.out.println(from + " just called this method from App");
    }
}














