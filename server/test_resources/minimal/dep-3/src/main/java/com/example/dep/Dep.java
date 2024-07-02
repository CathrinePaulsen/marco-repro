package com.example.dep;

/**
 * Minimal library
 */
public class Dep
{
    public static void main( String[] args )
    {
        System.out.println( "Hello World from Dep!" );
    }

    public static int add(int a, int b) {
        return a + b;
    }
    public static int mul(int a, int b) {
        return a * b;
    }
    public static void method(String from) {
        System.out.println(from + " just called this method from dep:3");
    }
}














