package com.example.dep;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class DepTest {
    @Test
    public void testAdd() {
        Dep dep = new Dep();
        assertEquals(4, dep.add(2, 2));
    }
    @Test
    public void testSub() {
        Dep dep = new Dep();
        assertEquals(1, dep.sub(2, 1));
    }
    @Test
    public void testMul() {
        Dep dep = new Dep();
        assertEquals(4, dep.mul(2, 2));
    }
}