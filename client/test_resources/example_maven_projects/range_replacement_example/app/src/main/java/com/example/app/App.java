package com.example.app;

import com.example.libA.LibA;
import com.example.libC.LibC;

/**
 * Hello world!
 *
 */
public class App
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from App!" );
        LibA.method("App");
        LibC.method("App");
    }

    public static void method(String from) {
        System.out.println(from + " just called this method from App");
    }
}














