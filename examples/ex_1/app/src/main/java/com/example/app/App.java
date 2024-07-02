package com.example.app;

import com.example.appA.AppA;
import com.example.appB.AppB;

/**
 * Hello world!
 *
 */
public class App
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from App!" );
        AppA.method("App");
        AppB.method("App");
    }

    public static void method(String from) {
        System.out.println(from + " just called this method from App");
    }
}














