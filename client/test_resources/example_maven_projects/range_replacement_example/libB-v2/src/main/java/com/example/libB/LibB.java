package com.example.libB;

/**
 * Hello world!
 *
 */
public class LibB
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from Lib B v2!" );
    }

    public static void method(String from, int version) {
        System.out.println(from + "v" + version + " just called this method from Lib B v2");
    }
}
