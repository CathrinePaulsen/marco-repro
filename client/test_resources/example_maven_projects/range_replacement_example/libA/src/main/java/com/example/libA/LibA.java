package com.example.libA;

import com.example.libB.LibB;

/**
 * Hello world!
 *
 */
public class LibA
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from Lib A!" );
    }

    public static void method(String from) {
        System.out.println(from + " is trying to call Lib B v2 via Lib A: ");
        LibB.method("    Lib A", 1);
//        LibB.method("Lib A");
    }
}
