package com.example.libC;

import com.example.libB.LibB;

/**
 * Hello world!
 *
 */
public class LibC
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from Lib C!" );
    }

    public static void method(String from) {
        System.out.println(from + " is trying to call Lib B v1 via Lib C: ");
        LibB.method("    Lib C");
    }
}
