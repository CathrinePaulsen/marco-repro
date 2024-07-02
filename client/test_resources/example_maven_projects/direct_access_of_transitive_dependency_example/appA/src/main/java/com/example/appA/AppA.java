package com.example.appA;

import com.example.appB.AppB;
import com.example.appC.AppC;

/**
 * Hello world!
 *
 */
public class AppA
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from A!" );
        AppB.method("A");
        AppC.method("A");
        com.example.appD.LibB.method("A");
    }

    public static void method(String from) {
        System.out.println(from + " just called this method from A");
    }
}














